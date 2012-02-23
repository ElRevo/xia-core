import socket, select, random
import struct, time, signal, os, sys
import fcntl
from xsocket import *
from ctypes import *

# Pretend a magic naming service givs us a dag for netloc...
from xia_address import *

def send_to_browser(data, browser_socket):
    try:
        browser_socket.send(data)
        return True
    except:
        print 'ERROR: xiaproxy.py: send_to_browser: error sending data to browser'
        browser_socket.close()
        return False
        
        

def recv_with_timeout(sock, timeout=5):
    # Make socket non-blocking
    try:
        fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)
    except IOError:
        print "ERROR: xiaproxy.py: recv_with_timeout: could not make socket nonblocking"
    
    # Receive data
    start_time = time.time()   # current time in seconds since the epoch
    received_data = False
    reply = '<html><head><title>XIA Error</title></head><body><p>&nbsp;</p><p>&nbsp;</p><p style="text-align: center; font-family: Tahoma, Geneva, sans-serif; font-size: xx-large; color: #666;">Sorry, something went wrong.</p><p>&nbsp;</p><p style="text-align: center; color: #999; font-family: Tahoma, Geneva, sans-serif;"><a href="mailto:xia-dev@cs.cmu.edu">Report a bug</a></p></body></html>'
    try:
        while (time.time() - start_time < timeout and not received_data):
            try:
	    	select.select([sock], [], [], 0.02)
                reply = Xrecv(sock, 65521, 0)
                received_data = True
            except IOError:
                received_data = False
            except:
                print 'ERROR: xiaproxy.py: recv_with_timeout: error receiving data from socket'
    except (KeyboardInterrupt, SystemExit), e:
        Xclose(sock)
        sys.exit()

    if (not received_data):
        print "Recieved nothing"
    	raise IOError

    return reply

def check_for_and_process_CIDs(message, browser_socket):
    rt = message.find('CID') 
    #print rt
    if (rt!= -1):
        http_header = message[0:rt]
        print "requesting for CID", message[rt+4:rt+44]
	try:
           content = requestCID(message[rt+4:rt+44])
	except:
	   print "closing browser_socket"
	   browser_socket.close() 
	   return True
	## this was the first occurrence
	send_to_browser(http_header, browser_socket)
	send_to_browser(content, browser_socket)
	## now keep finding CID and sending content
	#print "length received ",len(message)
	rt = message.find('CID', rt+44)
	while(rt != -1):
		print "requesting for CID", message[rt+4:rt+44]
		try:
		    content = requestCID(message[rt+4:rt+44])
		except:
		    print "closing browser_socket"
		    browser_socket.close() 
		    return True
		send_to_browser(content, browser_socket)
		rt = message.find('CID', rt+44)
	print "no more CID\n\n"
        return True
    #print "NO CID present"
    return False


def check_for_and_process_CIDlist(message, browser_socket):
    rt = message.find('CID') 
    print rt
    if (rt!= -1):
        http_header = message[0:rt]
	print "Sending first chunk \n";
        content = requestVideoCID(message[rt+4:rt+44], True)
	if (content==None):
            print "closing browser socket"
            browser_socket.close()
	    return False
	## this was the first occurrence
	#print header
	#print content
	send_to_browser(http_header, browser_socket)
	send_to_browser(content, browser_socket)
	## now keep finding CID and sending content
	#print "length received ",len(message)
	rt = message.find('CID', rt+44)
	while(rt != -1):
		print "requesting for CID", message[rt+4:rt+44]
		content = requestVideoCID(message[rt+4:rt+44], True)
	        if (content==None):
                    print "closing browser socket"
                    browser_socket.close()
	            return False
		send_to_browser(content, browser_socket)
		rt = message.find('CID', rt+44)
        return True
    print "NO CID present"
    return False

def process_more_CIDlist(message, browser_socket, moresock, socks):
    rt = message.find('CID') 
    #print rt
    cidlist = list()
    while(rt != -1):
        #print "requesting for CID", message[rt+4:rt+44]
        CID = message[rt+4:rt+44]
        content_dag = 'CID:%s' % CID
        #content_dag = 'RE %s %s %s' % (AD1, HID1, content_dag)
        content_dag = 'DAG 2 0 - \n %s 2 1 - \n %s 2 - \n %s' % (AD1, HID1, content_dag)
        cidlist.append(content_dag)
        #XgetCID(moresock, content_dag, len(content_dag))
        #content = Xrecv(moresock, 65521, 0)
        #browser_socket.send(content)
        rt = message.find('CID', rt+44)
    ## issue multiple request
    ## and receive multiple content
    ## first issue all the requests
    for i in range(len(cidlist)):
        try:
            XgetCID(socks[i], cidlist[i], len(cidlist[i]))
        except:
            print 'ERROR: xiaproxy.py: process_more_CIDlist: error requesting CID %s' % cidlist[i]
    ## then retrieve them
    for i in range(len(cidlist)):
        try:
            #content = recv_with_timeout(socks[i]) # = Xrecv(socks[i], 1024, 0)
            content = XreadCID(socks[i], 65521, 0, cidlist[i], len(cidlist[i]))
	except:
	    print "closing browser socket"
	    browser_socket.close()
	    return False	
        send_to_browser(content, browser_socket)
    return True

def process_videoCIDlist(message, browser_socket, socks):
    rt = message.find('CID') 
    #print rt
    cidlist = list()
    while(rt != -1):
	#print "requesting for CID", message[rt+4:rt+44]
	CID = message[rt+4:rt+44]
	content_dag = 'CID:%s' % CID
        #content_dag = 'RE %s %s %s' % (AD1, HID1, content_dag)
        content_dag = 'DAG 2 0 - \n %s 2 1 - \n %s 2 - \n %s' % (AD1, HID1, content_dag)
	cidlist.append(content_dag)
        #XgetCID(moresock, content_dag, len(content_dag))
        #content = Xrecv(moresock, 65521, 0)
	#browser_socket.send(content)
	rt = message.find('CID', rt+44)
    ## issue multiple request
    ## and receive multiple content
    ## first issue all the requests
    for i in range(len(cidlist)):
        try:
            XgetCID(socks[i], cidlist[i], len(cidlist[i]))
        except:
            print 'ERROR: xiaproxy.py: process_videoCIDlist: error requesting CID %s' % cidlist[i]
    ## then retrieve them
    for i in range(len(cidlist)):
        try:
            #content = recv_with_timeout(socks[i]) # = Xrecv(socks[i], 1024, 0)
            content = XreadCID(socks[i], 65521, 0, cidlist[i], len(cidlist[i]))
	except:
	    browser_socket.close()
	    print "closing browser socket"
	    return False
        if not send_to_browser(content, browser_socket):
            return False        
    return True


 
def sendVideoSIDRequest(netloc, payload, browser_socket):
    print "Debugging: in SID function - net location = ",netloc  

    sock = Xsocket(0)
    if (sock<0):
        print "error opening socket"
        return
    dag = "RE %s %s %s" % (AD1, HID1, SID_VIDEO) # Need a SID?
    print "Connecting to ",dag	
  
    status = Xconnect(sock, dag)
    if (status != 0):
       	print "Unexpected error:", sys.exc_info()[0]
       	Xclose(sock)
    	print "sendSIDRequest() Closing browser socket "
    	browser_socket.close()
	return
    
    print "Connected. OK\n"
    # Send request for number of chunks
    asknumchunks = "numchunks";
    Xsend(sock, asknumchunks, len(asknumchunks), 0)
    #Xsend(sock, payload, len(payload), 0)
    # Receive reply
    print 'sendSIDRequest: about to receive reply'
    try:
        reply = recv_with_timeout(sock) # = Xrecv(sock, 65521, 0)
    except:
        Xclose(sock)
    	print "closing browser socket"
	browser_socket.close()
	return

    Xclose(sock)
    numchunks = int(reply)
    print "sendSIDRequest: received reply for number of chunks ",numchunks

    ## may be send http header along with first content
    ## return ogg header
    http_header = "HTTP/1.0 200 OK\r\nDate: Tue, 01 Mar 2011 06:14:58 GMT\r\nConnection: close\r\nContent-type: video/ogg\r\nServer: lighttpd/1.4.26\r\n\r\n"


    ## next get chunks, at most 20 in a go
    threshold = 20
    socks = list()
    for i in range(threshold):
	sockcid = Xsocket(2)
	socks.append(sockcid)
    num_iterations = (numchunks/threshold) + 1
    for i in range(num_iterations):
        st_cid = i * threshold
        end_cid = (i+1) * threshold
        if(end_cid > numchunks):
            end_cid = numchunks
        cidreqrange = str(st_cid) + ":" + str(end_cid)
        print "Requesting for ",cidreqrange
        try:
            sock = Xsocket(0)

            status = Xconnect(sock, dag)

            if (status != 0):
            	print "Unexpected error:", sys.exc_info()[0]
        	Xclose(sock)
    		print "sendSIDRequest() Closing browser socket "
    		browser_socket.close()
		return

            Xsend(sock, cidreqrange, len(cidreqrange), 0)

        except:
            print 'ERROR: xiaproxy.py: sendVideoSIDRequest: error requesting cidreqrange %s' % cidreqrange
	
	try:
	    reply= recv_with_timeout(sock) # = Xrecv(sock, 1024, 0)
    	except:
     	    print "closing browser socket"
	    browser_socket.close()
	    break;

	Xclose(sock)
	#print reply
	if(i == 0):
    		send_to_browser(http_header, browser_socket)
	ret = process_videoCIDlist(reply, browser_socket, socks)
	if (ret==False):
	    break;
	## process CIDs 
    for i in range(threshold):
        Xclose(socks[i])
    return

def requestVideoCID(CID, fallback):
    sock = Xsocket(2)
    if (sock<0):
        print "error opening socket"
        return
    # Request content
    content_dag = 'CID:%s' % CID
    if fallback:
        content_dag = 'RE %s %s %s' % (AD1, HID1, content_dag)
    #print 'Retrieving content with ID: \n%s' % content_dag
    try:
        XgetCID(sock, content_dag, len(content_dag))
    except:
        print 'ERROR: xiaproxy.py: requestVideoCID: error requesting CID \n%s' % content_dag
    # Get content
    try:
        #data = recv_with_timeout(sock) # = Xrecv(sock, 65521, 0)
        data = XreadCID(sock, 65521, 0, content_dag, len(content_dag))
        #print 'Retrieved content:\n%s' % data
        Xclose(sock)
    except:
        return  None
    return data

def getrandSID():
    sid = "SID:"+ ("%040d"% int(random.random()*1e40))
    assert len(sid)==44
    return  sid

def sendSIDRequestXSP(ddag, payload, browser_socket):
    # Create socket
    sock = Xsocket(0)
    if (sock<0):
        print "ERROR: xiaproxy.py: sendSIDRequestXSP: could not open socket"
        return

    print "sendSIDRequestXSP()"
    print ddag

    #ddag = "DAG 0 1 - \n %s 2 - \n %s 2 - \n %s 3 - \n %s" % (AD1, IP1, HID1, sid)
    #ddag = "DAG 0 - \n %s 1 - \n %s 2 - \n %s 3 - \n %s" % (AD0, IP1, HID1, SID1)
    sid = getrandSID()
    sdag = "DAG 0 1 - \n %s 2 - \n %s 2 - \n %s 3 - \n %s" % (AD0, IP0, HID0, sid)    
    #sdag = "DAG 0 - \n %s 1 - \n %s 2 - \n %s 3 - \n %s" % (AD1, IP0, HID0, SID0)

    try:
        Xbind(sock, sdag)

        rtt = time.time() 
        # Connect to service
        status = Xconnect(sock, ddag)
        if (status != 0):
        	print "Unexpected error:", sys.exc_info()[0]
        	Xclose(sock)
    		print "sendSIDRequestXSP() Closing browser socket "
    		browser_socket.close()
		return
		       
        # Send request
        Xsend(sock, payload, len(payload), 0)
        
    except:
        print 'ERROR: xiaproxy.py: sendSIDRequestXSP: error binding to sdag, connecting to ddag, or sending SID request:\n%s' % payload

    # Receive reply and close socket
    try:
        #print "\n\n Waiting for reply... \n\n"
        reply= recv_with_timeout(sock) # Use default timeout
	if (reply.find("span")<0):
            print "Potentially non-ASCII payload from SID (len %d) " % len(reply)
    except IOError:
	print "Unexpected error:", sys.exc_info()[0]
        Xclose(sock)
    	print "sendSIDRequestXSP() Closing browser socket "
    	browser_socket.close()
	return 
    Xclose(sock)

    # Pass reply up to browswer if it's a normal HTTP message
    # Otherwise request the CIDs
    contains_CIDs = check_for_and_process_CIDs(reply, browser_socket)
    if not contains_CIDs:
	rtt = int((time.time()-rtt) *1000)
	# Use last modified field to embedd RTT info
        reply = reply.replace("Last-Modified: 100", ("Last-Modified:%d" % rtt)) # TODO: a bit of a hack
        send_to_browser(reply, browser_socket)
    return



def sendSIDRequestXDP(ddag, payload, browser_socket):
    # Create socket
    sock = Xsocket(XSOCK_DGRAM)
    if (sock<0):
        print "ERROR: xiaproxy.py: sendSIDRequestXDP: could not open socket"
        return

    #ddag = "DAG 0 1 - \n %s 2 - \n %s 2 - \n %s 3 - \n %s" % (AD1, IP1, HID1, sid)
    #ddag = "DAG 0 - \n %s 1 - \n %s 2 - \n %s 3 - \n %s" % (AD0, IP1, HID1, SID1)
    sid = getrandSID()
    sdag = "DAG 0 1 - \n %s 2 - \n %s 2 - \n %s 3 - \n %s" % (AD0, IP0, HID0, sid)    
    #sdag = "DAG 0 - \n %s 1 - \n %s 2 - \n %s 3 - \n %s" % (AD1, IP0, HID0, SID0)
    replyto =  ''
    reply_dag = ''

    try:

        rtt = time.time() 
        
        # Send request
        Xsendto(sock, payload, len(payload), 0, ddag, len(ddag)+1)
        
    except:
        print 'ERROR: xiaproxy.py: sendSIDRequestXDP: error binding to sdag, or sending SID request:\n%s' % payload

    # Receive reply and close socket
    try:
        (reply, reply_dag) = Xrecvfrom(sock, 65521, 0)
        #print "xiaproxy.py: reponse: %s" % reply
    except IOError:
        print "Unexpected error:", sys.exc_info()[0]
        Xclose(sock)
        print "sendSIDRequestXDP() Closing browser socket "
        browser_socket.close()
        return 
    Xclose(sock)
    
    # Pass reply up to browswer 
    rtt = int((time.time()-rtt) *1000)
    # Use last modified field to embedd RTT info
    reply = reply.replace("Last-Modified: 100", ("Last-Modified:%d" % rtt)) # TODO: a bit of a hack
    send_to_browser(reply, browser_socket)
    return    
       


def requestCID(CID):
    # TODO: fix issue where bare CIDs crash click
    print "in getCID function"  
    print CID

    sock = Xsocket(2)
    if (sock<0):
        print "error opening socket"
        return

    # Request content
    content_dag = 'CID:%s' % CID    
    content_dag = "DAG 3 0 1 - \n %s 3 2 - \n %s 3 2 - \n %s 3 - \n %s" % (AD1, IP1, HID1, content_dag)
    sid = getrandSID()
    sdag = "DAG 0 1 - \n %s 2 - \n %s 2 - \n %s 3 - \n %s" % (AD0, IP0, HID0, sid)       
    
    print 'Retrieving content with ID: \n%s' % content_dag
    try:
        Xbind(sock, sdag);
        XgetCID(sock, content_dag, len(content_dag))
    except:
        print 'ERROR: xiaproxy.py: requestCID: Error binding to socket or requesting CID'

    # Get content and close socket
    #data = recv_with_timeout(sock) # Use default timeout
    data = XreadCID(sock, 65521, 0, content_dag, len(content_dag))
    Xclose(sock)
    print "got CID value " +data[0:10]
    return data


def xiaHandler(control, path, payload, browser_socket):
    #print "in XIA code\n" + control + "\n" + payload
    
    # Configure XSocket
    set_conf("xsockconf_python.ini", "xiaproxy.py")
    #print_conf()  #for debugging
    control=control[4:]  # remove the 'xia.' prefix


    if payload.find('GET /favicon.ico') != -1:
                    return
    if control.find('sid') == 0:
        #print "SID request"
        if control.find('image.jpg') != -1: # TODO: why?
            payload = 'image.jpg'
        found_video = control.find('video')
        if(found_video != -1):
            sendVideoSIDRequest(control[4:], payload, browser_socket)
        elif(control.find('sid_stock') != -1):
            # For stock_service, use XDP (for testing purpose)
            ddag = dag_from_url(control + path)
            sendSIDRequestXDP(ddag, payload, browser_socket)         
        else:
            # Do some URL processing 
            ddag = dag_from_url(control + path)
            sendSIDRequestXSP(ddag, payload, browser_socket)  
    elif control.find('cid') == 0:
        print "CID request:\n%s" % control
        control_array = control.split('.')
        num_chunks = int(control_array[1])
        print "num chunks: %d" % num_chunks
        print 'CID list: %s' %control_array[2]
       
        # The browser might be requesting a list of chunks; if so, we'll recombine them into one object
        recombined_content = ''
        for i in range (0, num_chunks):
            print 'CID to fetch: %s' % control_array[2][i*40:40+i*40]
	    try:
                recombined_content += requestCID(control_array[2][i*40:40+i*40])
	    except:
	        print "Closing browser_socket"
	    	browser_socket.close()
	        return
            
        length = len (recombined_content)
        print "recombined_content length %d " % length
        send_to_browser(recombined_content, browser_socket)
    return

