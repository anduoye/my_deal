#!/usr/bin/python
# -*- coding: utf8 -*-
import sys
import json
import socket

COOKIE = 234567


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
        print ("req_str:",req_str)
        conn.send(req_str)
    except socket.timeout:
    #except Exception as e:
        #print e
        print ("time out")
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
        print ("获取服务器响应错误。")
        sys.exit()


# OrderSide: 0---买入, 1---卖出
# order_type: 增强限价单(普通交易)
# price: 交易价格
# qty:交易数量
# stock_code:股票代码
def place_order(conn, order_side, order_type, price, qty, stock_code):
    global COOKIE
    req_param = {"EnvType":"0", "Cookie":str(COOKIE), "OrderSide":str(order_side), "OrderType":str(order_type), "Price":str(price), "Qty":str(qty), "StockCode":stock_code}
    COOKIE += 1
    order_success = True
    
    import time
    time.sleep(1.5)         #按照要求，30s内不能交易超过20次。
    
    #analyzed_rsps_arr = send_req_and_get_rsp(self._conn, 6003, req_param, 1)
    analyzed_rsps_arr = send_req_and_get_rsp(conn, 7003, req_param, 1)
    print ("已经下单成功：价格：%s,数量：%s" % (str(price),str(qty)))
    
#     if analyzed_rsps_arr is not None:
#         for analyzed_rsps in analyzed_rsps_arr:
#             if int(analyzed_rsps["ErrCode"]) != 0:
#                 order_success = False
#                 print analyzed_rsps["ErrDesc"],"购买或出售错误，退出。"
#                 return
    while order_success:                                  #轮询检查当前cookie的交易状态，直到查询到”全部成交“
        if deal_status_ok(conn,COOKIE):
            print ("交易成功。")
            return order_success
        else:
            continue

#{"Protocol":"7008","ReqParam":{"Cookie":"123123","EnvType":"0"},"Version":"1"}
def deal_status_ok(conn,Cookie):
    req_param = {"Cookie":str(Cookie),"EnvType":"0"}
    analyzed_rsps_arr = send_req_and_get_rsp(conn, 7008, req_param, 1)
    order_array = analyzed_rsps_arr["USOrderArr"]
    if order_array:
        '''现在要求每次只交易一支股票，'''
        print ("等待成交中。。。")
        return 3 == int(order_array[0]["Status"])
    
        
    
    