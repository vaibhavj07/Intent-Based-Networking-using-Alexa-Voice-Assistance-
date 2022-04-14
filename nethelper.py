import redis
import pickle
import networkx as nx
import matplotlib.pyplot as plt
import csv


rclient = redis.StrictRedis(host="localhost")

def update_value(value):
    pvalue = pickle.dumps(value)
    rclient.set(str(KEYNAME), pvalue)

def get_all():
    result = {}
    for key in rclient.scan_iter():
        pval = rclient.get(key)
        val = pickle.loads(pval)
        result[key.decode('utf-8')] = val
    return result

def write_csv_file(swname, stats):
    fname = "switch_"+ str(swname) + "_portstats.csv"
    writ = csv.writer(open(fname, 'w', buffering=1), delimiter=',')
    header = ["port_no","tx_kbps","rx_kbps"]
    writ.writerow(header)
    for portst in stats:
        #{"port": port_stats.port_no, "tx_kbps": tx_kbps, "rx_kbps": rx_kbps} 
        row = [str(portst["port"]), str(portst["tx_kbps"]), str(portst["rx_kbps"])]
        writ.writerow(row)

def draw_topology():
    topo = get_all()['topology']
    print(topo)
    networkx = None
    networkx = nx.DiGraph()
    for s in topo["switches"]:
        networkx.add_node(s, name=s)
    for host in topo["hosts"]:
        networkx.add_node(host[0], name=host[0])
        networkx.add_edge(host[0],host[1],weight=1)
    for l in topo["links"]: 
        networkx.add_edge(l[0],l[1],weight=1)
    nx.draw(networkx, with_labels=True, font_weight='bold') 
    plt.savefig("Graph.png", format="PNG")


def calculate_switch_stats(sw, sw_stats):
    no_of_ports = len(sw_stats)
    total_utilization = 0
    for p in sw_stats:
        total_utilization = total_utilization + p['tx_kbps'] + p['rx_kbps']
        if p['tx_kbps'] > 3000 or p['rx_kbps'] > 3000 :
            print(sw, p['port'],"is congested")

    if total_utilization > (no_of_ports * 3000):
        print("switch is congested", sw, "total_utilization ", total_utilization)


def switch_stats():
    sws= get_all()['topology']['switches']
    for sw in sws:
        hdg = "switch_"+str(sw)+"_portstats"
        sw_stats = get_all()[hdg]
        print(sw, sw_stats)
        write_csv_file(sw,sw_stats)
        #calculate_switch_stats(sw, sw_stats)
    return("switch csv files generated")


def highest_utilized_switch():
    highest_util = None
    highest_util_sw = 0
    #congested switch
    sws= get_all()['topology']['switches']
    for sw in sws:
        hdg = "switch_"+str(sw)+"_portstats"
        sw_stats = get_all()[hdg]
        print(sw, sw_stats)
        
        total_u = 0
        for pst in sw_stats:
            total_u = total_u + (pst['tx_kbps'] + pst['rx_kbps'])
        

        if highest_util == None:
            highest_util = total_u
            highest_util_sw = sw

        elif highest_util < total_u:
            highest_util = total_u
            highest_util_sw = sw

    result = "Highest utilized switch is " + str(highest_util_sw) + " bandwidth is " + str(highest_util) + " Mbps"
    print(result)
    return(result)


def highest_utilized_link():
    #highest_utilized_link
    highest_util_port = None
    highest_util_sw = 0
    highest_util_port_no = 0
    #congested switch
    sws= get_all()['topology']['switches']
    for sw in sws:
        hdg = "switch_"+str(sw)+"_portstats"
        sw_stats = get_all()[hdg]
        print(sw, sw_stats)
        
        total_u = 0
        for pst in sw_stats:

            if highest_util_port == None:
                highest_util_port = pst['tx_kbps'] + pst['rx_kbps']
                highest_util_sw = sw
                highest_util_port_no = pst['port']

            elif highest_util_port <  (pst['tx_kbps'] + pst['rx_kbps']):
                highest_util_port =  pst['tx_kbps'] + pst['rx_kbps']
                highest_util_port_no = pst['port']
                highest_util_sw = sw

    result = "Highest utilized port is " + str(highest_util_port_no) + " bandwidth is " + str(highest_util_port) + "Mbps in switch " + str(highest_util_sw)
    print(result)
    return(result)
#update_value(1)
#draw_topology()
#switch_stats()
#highest_utilized_link()
#highest_utilized_switch()
#draw_topology()