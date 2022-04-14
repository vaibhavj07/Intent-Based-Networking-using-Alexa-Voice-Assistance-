#app.py consists of L3 Simple Switch + topology discovery + port-stats in DB file
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4

from ryu.lib import hub
import networkx as nx
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link, get_host
import random
from time import sleep
import sqlite3, re, calendar, time, copy

from time import sleep
import redis
import pickle
keystore = {}
INTERVAL = 10

rclient = redis.StrictRedis(host="localhost")
def get_all():
    result = {}
    for key in rclient.scan_iter():
        pval = rclient.get(key)
        val = pickle.loads(pval)
        result[key.decode('utf-8')] = val
    return result
def update_value(key, value):
    pvalue = pickle.dumps(value)
    rclient.set(str(key), pvalue)


def calculate_value(key, val):
    key = str(key).replace(".", "_")
    if key in keystore:
        oldval = keystore[key]
        cval = (val - oldval) / INTERVAL
        # storing the val
        keystore[key] = val
        return cval
    else:
        keystore[key] = val
        return 0


class L3Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L3Switch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.topology_api_app = self
        self.topodiscovery_thread = hub.spawn(self._tdiscovery)    
        self.hosts = []
        self.links = []
        self.switches = []
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

    def _tdiscovery(self):
        #while True:
        hub.sleep(10)
        self.get_topology_data()

    def _monitor(self):
        while True:
            self.logger.info(" start monitoring")
            for dp in self.datapaths.values():
                self.request_port_metrics(dp)
            hub.sleep(INTERVAL)
            
    def request_port_metrics(self, datapath):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPPortStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls([ofp_event.EventOFPPortStatsReply], MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        hdr = "switch_" + str(ev.msg.datapath.id)
        result = []
        for port_stats in ev.msg.body:
            if port_stats.port_no == 4294967294:
                #ignore the local port
                continue
            print(port_stats)
            #PORT_STATS_DB[ev.msg.datapath.id].setdefault(port_stats.port_no, [])
            txhdr = hdr + str(port_stats.port_no) + ".tx_bytes"
            #calculate the tx bytes rate (per second)            
            txbytes = calculate_value(txhdr, int(port_stats.tx_bytes))
            rxhdr = hdr + str(port_stats.port_no) + ".rx_bytes"
            #calculate the rx bytes rate (per second)                        
            rxbytes = calculate_value(rxhdr, int(port_stats.rx_bytes))
            
            tx_kbps = (txbytes * 8) / 1000
            rx_kbps = (rxbytes * 8) / 1000
            #total bytes per second
            totkbps = tx_kbps + rx_kbps
            # update it in redis kv

            result.append( {"port": port_stats.port_no, "tx_kbps": tx_kbps, "rx_kbps": rx_kbps, "tot_kbps": totkbps} )

        hdr = "switch_" + str(ev.msg.datapath.id) +"_portstats"
        update_value(hdr, result)


    def get_topology_data(self):        
        switch_list = get_switch(self.topology_api_app, None)
        self.switches = [switch.dp.id for switch in switch_list]
        links_list = get_link(self.topology_api_app, None)
        self.links = [(link.src.dpid, link.dst.dpid, {'port': link.src.port_no}) for link in links_list]
        host_list = get_host(self.topology_api_app, None)
        self.hosts = [(host.mac, host.port.dpid, {'port': host.port.port_no}) for host in host_list]
        self.logger.info("switches %s", self.switches)
        self.logger.info("links %s", self.links)
        self.logger.info("hosts %s", self.hosts)
        #self.build_topology()
        #update DB about topology data
        update_value("topology", {"switches": self.switches, "links": self.links, "hosts": self.hosts})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)


    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_t=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,idle_timeout=idle_t,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,idle_timeout=idle_t,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:

            # check IP Protocol and create a match for IP
            if eth.ethertype == ether_types.ETH_TYPE_IP:
                ip = pkt.get_protocol(ipv4.ipv4)
                srcip = ip.src
                dstip = ip.dst
                match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                        ipv4_src=srcip,
                                        ipv4_dst=dstip
                                        )
                # verify if we have a valid buffer_id, if yes avoid to send both
                # flow_mod & packet_out
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, 1, match, actions, msg.buffer_id, idle_t=10)
                    return
                else:
                    self.add_flow(datapath, 1, match, actions, idle_t=10)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)