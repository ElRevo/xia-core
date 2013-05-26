#!/usr/bin/python

import rpyc, re, time, threading, thread
from check_output import check_output
from rpc import rpc
from subprocess import call, Popen, PIPE
from rpyc.utils.server import ThreadedServer

RPC_PORT = 43278
KILL_XIANET = 'sudo ~/fedora-bin/xia-core/bin/xianet stop'
XROUTE = '/home/cmu_xia/fedora-bin/xia-core/bin/xroute -v'
MASTER_SERVER = 'GS11698.SP.CS.CMU.EDU'
BEAT_PERIOD = 3
BROADCAST_HID = 'ffffffffffffffffffffffffffffffffffffffff'
PING_INTERVAL = .25
PING_COUNT = 4

myHID = ''
my_name = check_output("hostname")[0].strip()

finishEvent = threading.Event()

def exec_fun(fun):
    exec(fun)

def multi_ping(neighbors):
    pingcmd = 'sudo ping -W 1 -i %s -c' % PING_INTERVAL
    
    processes = [Popen('%s %s %s' % (pingcmd, 1, neighbor), shell=True, stdout=PIPE, stderr=PIPE) for neighbor in neighbors]
    outs = [process.communicate() for process in processes]

    processes = [Popen('%s %s %s' % (pingcmd, PING_COUNT, neighbor), shell=True, stdout=PIPE, stderr=PIPE) for neighbor in neighbors]
    outs = [process.communicate() for process in processes]
    rcs = [process.wait() for process in processes]
    outs = zip(outs, rcs)

    #print '<<<< PING RESULTS: %s >>>>' % outs

    stats = []
    for out in outs:
        host = out[0][0].split('\n')[0].split(' ')[1]
        p = float(out[0][0].split("\n")[-2].split('=')[1].split('/')[1]) if out[1] == 0 else 5000.00
        stats.append((p,host))
    stats = sorted(stats)
    stats = [(-1,stat[1]) if stat[0] == 5000 else stat for stat in stats]
    stats = [("%.3f" % stat[0], stat[1]) for stat in stats]
    return stats

def traceroute(neighbor):
    out = check_output('sudo traceroute -I -w 1 %s' % neighbor)
    stat = int(out[0].split("\n")[-2].strip().split(' ')[0])
    stat = -1 if stat is 30 else stat
    return stat

def xping(neighbor,tryUntilSuccess=True):
    while tryUntilSuccess:
        xpingcmd = '/home/cmu_xia/fedora-bin/xia-core/bin/xping -i %s -c' % PING_INTERVAL
        s = '%s %s "%s"' % (xpingcmd, 1, neighbor)
        print s
        check_output(s)
        s = '%s %s "%s"' % (xpingcmd, PING_COUNT, neighbor)
        print s
        out = check_output(s)
        print out
        try:
            stat = "%.3f" % float(out[0].split("\n")[-2].split('=')[1].split('/')[1])
            break
        except:
            stat = -1
        stat = -1 if stat == '=' else stat
    return stat

def xtraceroute(neighbor):
    out = check_output('/home/cmu_xia/fedora-bin/xia-core/bin/xtraceroute "%s"' % neighbor)
    stat = int(out[0].split('\n')[-2].split('=')[1].strip())
    stat = -1 if stat is 30 else stat
    return stat
    
class MyService(rpyc.Service):
    def on_connect(self):
        self._conn._config['allow_pickle'] = True
        # code that runs when a connection is created
        # (to init the serivce, if needed)
        pass

    def on_disconnect(self):
        # code that runs when the connection has already closed
        # (to finalize the service, if needed)
        pass

    def exposed_gather_stats(self):
        print '<<<<GATHER STATS>>>>'
        neighbors = rpc(MASTER_SERVER, 'get_backbone', ())
        out = multi_ping(neighbors)
        latency = out[0][0]
        my_backbone = out[0][1]
        hops = traceroute(my_backbone)
        rpc(MASTER_SERVER, 'stats', (my_backbone, latency, hops))
        return ['Sent stats: (%s, %s, %s)' % (my_backbone, latency, hops), my_backbone]

    def exposed_gather_xstats(self):
        print '<<<<GATHER XSTATS>>>>'
        neighbor = rpc(MASTER_SERVER, 'get_neighbor_xhost', ())
        print 'neighbor: %s' % neighbor
        xlatency = xping(neighbor)
        print 'xlatency: %s' % xlatency
        xhops = xtraceroute(neighbor)
        print 'xhops: %s' % xhops
        rpc(MASTER_SERVER, 'xstats', (xlatency, xhops))
        return 'Sent xstats: (%s, %s, %s)' % (neighbor, xlatency, xhops)

    def exposed_get_hid(self):
        xr_out = check_output(XROUTE)
        return re.search(r'HID:(.*) *-2 \(self\)', xr_out[0]).group(1).strip().lower()

    def exposed_get_ad(self):
        xr_out = check_output(XROUTE)
        return re.search(r'AD:(.*) *-2 \(self\)', xr_out[0]).group(1).strip().lower()

    def exposed_get_neighbors(self):
        xr_out = check_output(XROUTE)
        neighbors = []
        for xline in xr_out[0].split('\n'):
            try:
                neighbors.append(re.split(' *',xline)[4].split(':')[1])
            except:
                pass
        neighbors = list(set(neighbors))
        neighbors = [neighbor.lower() for neighbor in neighbors]
        myHID = self.exposed_get_hid()
        if myHID in neighbors: neighbors.remove(myHID)
        if BROADCAST_HID in neighbors: neighbors.remove(BROADCAST_HID)
        return neighbors


    def exposed_soft_restart(self, neighbor):
        xianetcmd = rpc(MASTER_SERVER, 'get_xianet', (neighbor, ))
        check_output(KILL_XIANET)
        print 'running %s' % xianetcmd
        thread.start_new_thread(exec_fun, (xianetcmd, ))
        return xianetcmd

    def exposed_wait_for_neighbor(self, neighbor, msg):
        out = None
        while out == None:
            try:
                out = rpc(neighbor, 'get_hid', ())
            except:
                print msg
                time.sleep(1)
        return out

    def exposed_hard_stop(self):
        kill_cmd = rpc(MASTER_SERVER, 'get_kill', ())
        print kill_cmd
        call(kill_cmd,shell=True)
        sys.exit(0)


class Mapper(threading.Thread):
    def __init__(self, goOnEvent):
        super(Mapper, self).__init__()
        self.goOnEvent = goOnEvent

    def run(self):
        hb_serv = rpyc.connect(MASTER_SERVER, RPC_PORT)
        while self.goOnEvent.isSet():
            try:
                myHID = rpc('localhost', 'get_hid', ())
                neighbors = rpc('localhost', 'get_neighbors', ())
                hb_serv.root.heartbeat(myHID, neighbors)
                print 'HB: %s %s' % (myHID, neighbors)
            except Exception, e:
                try:
                    hb_serv = rpyc.connect(MASTER_SERVER, RPC_PORT)
                except:
                    pass
                pass
            time.sleep(BEAT_PERIOD)


class Runner(threading.Thread):
    def run(self):
        try:
            print 'requesting commands!'
            commands = rpc(MASTER_SERVER, 'get_commands', ())
            print 'commands received!'
            print 'commands: %s' % commands
            for command in commands:
                print command
                exec(command)
        except Exception, e:
            print e
            while True:
                try:
                    rpc(MASTER_SERVER, 'error', ('Runner', ))
                except:
                    print 'Failed to report error!! retrying'
                    time.sleep(1)
                else:
                    break

if __name__ == '__main__':
    print ('RPC server listening on port %d\n'
        'press Ctrl-C to stop\n') % RPC_PORT

    finishEvent.set()
    mapper = Mapper(goOnEvent = finishEvent)
    mapper.start()

    runner = Runner()
    runner.start()

    try:
        t = ThreadedServer(MyService, port = RPC_PORT)
        t.start()
    except Exception, e:
        print e
        rpc(MASTER_SERVER, 'error', ('RPC Server', ))

    print 'Local_Server Exiting, please wait...'
    finishEvent.clear()
    mapper.join()
    runner.join()

    print 'Local_Server Finished.'
