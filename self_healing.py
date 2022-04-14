import csv, os, threading, re, time, subprocess



SDN_NETWORK_TRUTH="network_truth.csv"
#gloabal
truth_config = []


def run_cmd(cmd):
    try:
        print(str(cmd))
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        #print(output)
        output = output.decode('utf-8')
        #print(output)
        return output
        #return subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as ex:
        if ex.returncode == 255:
            raise RuntimeWarning(ex.output.strip())
        raise RuntimeError('cmd execution returned exit status %d:\n%s'
                % (ex.returncode, ex.output.strip()))

#Read input file
def read_truth_info():
    global truth_config
    if os.path.isfile(SDN_NETWORK_TRUTH):
        with open(SDN_NETWORK_TRUTH) as csvfile:
            reader=csv.reader(csvfile)
            for row in reader:
                if row[0]!= "Switch DPID":
                    print(row)
                    truth_config.append({"dpid": row[0], "name": row[1], "controller": row[2], "of_version": row[3]})
            csvfile.close()


def perform_version_check(sw):
    '''
    read the the version
      - if version mismatch, remove controller, fix the version, update the controller
    '''
    #sudo ovs-vsctl get bridge s1 protocols
    output = run_cmd(["sudo","ovs-vsctl", "get", "bridge", sw["name"], "protocols"])
    #output is [OpenFlow13]. we need to remove [,] character. hence 1 and -2 index used
    op = output[1:-2]
    if op == sw["of_version"] :
        print("of version match")
        return    
    print("{} of version not match..expected version {} current version {}".format(sw["name"],sw["of_version"],op))
    output = run_cmd(["sudo","ovs-vsctl", "del-controller", sw["name"]])
    output = run_cmd(["sudo","ovs-vsctl", "set", "bridge", sw["name"], "protocols="+sw["of_version"]])
    output = run_cmd(["sudo","ovs-vsctl", "set-controller", sw["name"], sw["controller"]])



def perform_controller_check(sw):
    '''
    read the controller is connected, if not
      - update the controller
    '''
    output = run_cmd(["sudo","ovs-vsctl", "show"])
    output= output.split('\n')
    #print(output)
    bname = "Bridge "+sw["name"]
    print(bname)
    index = 0
    for i in output:
        if i.strip() == bname:
            #print("Found")
            #print(output[index+2], output[index+3])
            k = output[index+2]
            k1 = output[index+3]
            if "is_connected: true" in [k.strip(), k1.strip()]:
                print("{}Controller is connected".format(sw["name"]))
                return
            else:
                print("{}controller is NOT connected.. Fixing it".format(sw["name"]))
                #fix it
                output = run_cmd(["sudo","ovs-vsctl", "set-controller", sw["name"], sw["controller"]])
                return
        index  = index + 1




def detect_fix_errors():
    for sw in truth_config:
        perform_version_check(sw)

    for sw in truth_config:
        perform_controller_check(sw)


def heal_my_network():
    read_truth_info()
    detect_fix_errors()


#heal_my_network()