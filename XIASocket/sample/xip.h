#ifndef _XIP_H_
#define _XIP_H_

#define XIA_XID_ID_LEN        20

typedef struct xia_xid {
  uint32_t type;
  uint8_t id[XIA_XID_ID_LEN];
} xia_xid;

#pragma pack(push)
#pragma pack(1)     // without this, the size of the struct would not be 1 byte 
typedef struct xia_xid_edge
{
  //#if CLICK_BYTE_ORDER == CLICK_LITTLE_ENDIAN
  unsigned idx : 7;                   // index of node this edge points to 
  unsigned visited : 1;               // visited edge? 
  //#elif CLICK_BYTE_ORDER == CLICK_BIG_ENDIAN
  //unsigned visited : 1;
  //unsigned idx : 7;
  //#else
  //#   error "unknown byte order"
  //#endif
} xia_xid_edge;
#pragma pack(pop)

#define XIA_XID_EDGE_NUM      4
#define XIA_XID_EDGE_UNUSED   127u

typedef struct xia_xid_node {
  xia_xid xid;
  xia_xid_edge edge[XIA_XID_EDGE_NUM];
} xia_xid_node;

// XIA network layer packet header                                                                                                                                                                                                            
struct xip {
  uint8_t ver;                        /* header version */
  uint8_t nxt;                        /* next header */
  uint16_t plen;                      /* payload length */
  uint8_t dnode;                      /* total number of dest nodes */
  uint8_t snode;                      /* total number of src nodes */
  //uint8_t dints;                                                                                                                                                                                                                          
  //uint8_t sints;                                                                                                                                                                                                                          
  int8_t last;                        /* index of last visited node (note: integral) */
  uint8_t hlim;                       /* hop limit */
  xia_xid_node node[0];         /* XID node list */
};


#endif
