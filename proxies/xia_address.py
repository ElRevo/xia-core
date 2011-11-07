XIDS = dict(hid0="HID:0000000000000000000000000000000000000000",
hid1= "HID:0000000000000000000000000000000000000001",
hid2= "HID:000000000000000000000000000000eeeeee0000",
ad0=  "AD:1000000000000000000000000000000000000000",
ad1=  "AD:1000000000000000000000000000000000000001",
ad_cmu= "AD:1008888888888777777333555555555555500001",
rhid0="HID:0000000000000000000000000000000000000002",
rhid1="HID:0000000000000000000000000000000000000003",
rhid2="HID:0000000000000000000000000000000000000004",
sid0= "SID:0f00000000000000000000000000000000000055",
ip1="IP:128.2.208.167",
ip0="IP:71.206.239.67",
xiaweb= "SID:f0afa824a36f2a2d95c67ff60f61200e48006625",
video= "SID:1f10000001111111111111111111111110000056",
sid_stock= "SID:0f03333333333333333333333333330000000055")

SID_VIDEO= XIDS['video'] 
HID0= XIDS['hid0'] 
HID1= XIDS['hid1']
HID2= XIDS['hid2']
AD0=  XIDS['ad0'] 
AD1=  XIDS['ad1'] 
AD_CMU=XIDS['ad_cmu'] 
RHID0=XIDS['rhid0'] 
RHID1=XIDS['rhid1'] 
RHID2=XIDS['rhid2'] 
SID0= XIDS['sid0'] 
SID1= XIDS['xiaweb'] 
SID_STOCK= XIDS['sid_stock']

IP1 = XIDS['ip1']
IP0 = XIDS['ip0']



# Note: this is temporary. Eventually URLs will be formatted
# differently and name translation will use DNS
#
# Fallbacks are very limited; for a primary intent of an SID,
# the fallback must be AD:HID:SID; likewise, for CID, fallback
# must be AD:HID:CID
def dag_from_url(url): 
    #url_segments[0] = primary intent
    #url_segments[1] = fallback (if supplied)
    url_segments = url.split('fallback')

    # First segment is primary intent
    if url_segments[0][0:3] == 'sid':
        # If we're routing to a service, the service might be a
        # webserver, so we may have specified a page to retrieve;
        # if this is the case, don't include the page name in the
        # service name
        sid_request_segments = url_segments[0].split('/')
        primary_XID = xid_from_name(sid_request_segments[0][4:], 'SID')
    elif url_segments[0][0:3] == 'cid':
        primary_XID = xid_from_name(url_segments[0][4:], 'CID')
    else:
        print 'ERROR: dag_from_url: unsupported primary intent principal type'
        return

    # Check if a fallback was supplied
    # NOTE: this is very brittle; once we settle on
    # a URL format, we need better code here
    if len(url_segments) > 1:
        # Fallback provided
        url_segments[1] = url_segments[1][1:-1] # strip off parens

        fallback_segments = url_segments[1].split(':')
        final_node_num = len(fallback_segments) - 1

        dag = 'DAG'
	# we need to go for the iterative refinement (rather than kind of source routing....)
	dag += ' %i' % int(final_node_num)
        for j in range(0, final_node_num):
            dag += ' %i' % j
        for i in range(0, len(fallback_segments)):
            node_segments = fallback_segments[i].split('.')
            node_xid = xid_from_name(node_segments[1], node_segments[0].upper())
            dag += ' - \n %s' % (node_xid) # Add next node XID
            if i != len(fallback_segments) - 1: # last node has no outgoing edges
		dag += ' %i' % int(final_node_num)
                for j in range(i+1,  final_node_num): # add outgoing edges
                    dag += ' %i' % j
                #dag += '%i %i' % (final_node_num, i+1) # Add outgoing edges

        print dag
        return dag
    else:
        # No fallback
        # Use magic nameservice to get a fallback
        #dag = "DAG 0 1 - \n %s 2 - \n %s 2 - \n %s 3 - \n %s" % (AD1, IP1, HID1, primary_XID)
	dag = "DAG 3 0 1 - \n %s 3 2 - \n %s 3 2 - \n %s 3 - \n %s" % (AD1, IP1, HID1, primary_XID)

        # Don't use nameservice
        # dag = 'RE %s' % primary_XID

        return dag
    
def xid_from_name(name, xid_type='SID'):
    try:
        return XIDS[name] # If name is in XIDS, it must be human readable, so translate to XID
    except KeyError:
        print 'WARNING: xid_from_name: \'%s\' not found in dict XIDS. Could be an error.' % name
        return '%s:%s' % (xid_type, name) # If not, just return name, as it may already be an XID (but could be a typo)
