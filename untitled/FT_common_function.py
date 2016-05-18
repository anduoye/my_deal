#!/usr/bin/python
# -*- coding: utf8 -*-

import json
import socket

COOKIE = 8888


def json_analyze_rsps(rsp_str):
    ret_data_arr = []
    rsp_ar = rsp_str.split("\r\n")
    for rsp in rsp_ar:
        if len(rsp) <= 0 :
            continue
        rsp_after_json_analyze = json.loads(rsp)
        ret_data_arr.append(rsp_after_json_analyze)
    return ret_data_arr


def send_req_and_get_rsp(conn, protocol_code, req_param, protocol_version): #发包
    try:
        req = {"Protocol":str(protocol_code), "ReqParam":req_param, "Version":str(protocol_version)}
        req_str = json.dumps(req) + "\r\n"
        conn.send(req_str)
    except socket.timeout:
    #except Exception as e:
        #print e
        print "time out"
        return
    buf_size = 50       #收包
    rsp_str = ""
    while True:
        buf = conn.recv(int(buf_size))
        rsp_str += buf
        if len(buf) < int(buf_size):
            break
    res_dic = json_analyze_rsps(rsp_str)        #回包josn解析

    if int(res_dic[0]["ErrCode"]) == 0:
        if res_dic[0]["RetData"] is not None:
            return res_dic[0]["RetData"]
    else:
        print "occured error in response!"
        return


# OrderSide: 0---买入, 1---卖出
# order_type: 增强限价单(普通交易)
# price: 交易价格
# qty:交易数量
# stock_code:股票代码
def place_order(self, order_side, order_type, price, qty, stock_code):
    global COOKIE
    req_param = {"EnvType":"1", "Cookie":str(COOKIE), "OrderSide":str(order_side), "OrderType":str(order_type), "Price":str(price), "Qty":str(qty), "StockCode":stock_code}
    COOKIE += 1

    analyzed_rsps_arr = send_req_and_get_rsp(self._conn, 6003, req_param, 1)

    order_success = True
    if analyzed_rsps_arr is not None:
        for analyzed_rsps in analyzed_rsps_arr:
            if int(analyzed_rsps["ErrCode"]) != 0:
                order_success = False
                print analyzed_rsps["ErrDesc"]

    if order_success:
        print "交易成功"

    return order_success

