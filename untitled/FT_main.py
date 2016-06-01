#!/usr/bin/python
# -*- coding: utf8 -*-


import socket
import json
import sys

from FT_common_function import *


class FT:
    def __init__(self, code):
        self._code = code
        self._conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            self._conn.connect(("localhost", 11111))
        except Exception as e:
            print "连接FTNN错误，退出程序！!", e

    def __del__(self):
        self._conn.close()
        print "连接FTNN结束."

    def get_cur_price(self):
        # req_param = {'Market':'1','StockCode':'%s' % str(self._code)}  #Market:港股，StockCode:股票代码
        req_param = {'Market':'2','StockCode':'%s' % str(self._code)}    # 测试用：Market:美股，StockCode:股票代码
        data = send_req_and_get_rsp(self._conn, 1001, req_param, 1)    #获取当前股票基础信息
        real_price = int(data["Cur"])
        return real_price

    def get_stock_gear(self, get_gear_num):
        #req_param = {"Market":"1",'StockCode':'%s' % str(self._code),"GetGearNum":str(get_gear_num)}
        req_param = {"Market":"2",'StockCode':'%s' % str(self._code),"GetGearNum":str(get_gear_num)} # 测试用：Market:美股，StockCode:股票代码
        analyzed_rsps = send_req_and_get_rsp(self._conn,1002,req_param,1)
        try:
            dic_gear_info_lst = analyzed_rsps["GearArr"]
            if dic_gear_info_lst is None:
                print "获取买卖档口错误."
                return
        except TypeError,e:
            print "股票输入错误：" + '\n',e
            sys.exit()
            
        # buy_price_one  = dic_gear_info_lst[0]["BuyPrice"]   # 暂且认为当前市场上出价的第一把交易能满足我的需求
        # sell_price_one = dic_gear_info_lst[0]["SellPrice"]  # 暂且认为当前市场上出价的第一把交易能满足我的需求
        return dic_gear_info_lst


    '''
    account_info_rsp = {
                    "Cookie":"123456","DJZJ":"0","EnvType":"0","GPBZJ":"0","KQXJ":"3411240",
                    "Power":"3411240", #购买力
                    "XJJY":"3411240","YYJDE":"0",
                    "ZCJZ":"3497490",  #资产净值
                    "ZGJDE":"0","ZQSZ":"86250","ZSJE":"0"},
    '''
    def get_account_info(self):
        req_param = {"Cookie":"123456","EnvType":"0"}

        # account_info_rsp = send_req_and_get_rsp(self._conn, 6007, req_param, 1)
        account_info_rsp = send_req_and_get_rsp(self._conn, 7007, req_param, 1)  # 测试用：Market:美股，StockCode:股票代码
        return account_info_rsp["Power"], account_info_rsp["ZCJZ"]

    def check_on_hold(self):
        req_param = {"Cookie":"123457","EnvType":"0"}
        #on_hold_dict = send_req_and_get_rsp(self._conn, 6009, req_param, 1)
        on_hold_dict = send_req_and_get_rsp(self._conn, 7009, req_param, 1)  # 测试用：Market:美股，StockCode:股票代码
        #on_holded_stock_lst = on_hold_dict["HKPositionArr"]
        on_holded_stock_lst = on_hold_dict["USPositionArr"]  # 测试用：Market:美股，StockCode:股票代码

        return on_holded_stock_lst


# stcokcode: 股票代码
# lowline: 止损线
# upline: 止盈线
# controlline: 交易触发线
class DEAL():
    def __init__(self, stockcode, lowline, upline, controlline, meishou, fst_price):
        self.stockcode = stockcode
        self.lowline = lowline
        self.upline = upline
        self.controlline = controlline
        self.meishou = meishou
        self.fst_price = fst_price
        self.ft = FT(stockcode)

    # 检查持仓列表
    def i_have_hold(self):
        hold_lsts = self.ft.check_on_hold()
        return hold_lsts

    def trade(self):
        i_have = self.i_have_hold()
        hold_stock_lst = []
        if i_have:
            hold_stock_lst = [hold_lst["StockCode"] for hold_lst in i_have]  # 已经持有的股票代码，列表
            if str(self.stockcode) in hold_stock_lst:
                print "该股票已在持仓列表中，开始高频交易。。。"
                for hold_lst in i_have:
                    if hold_lst.get("StockCode") == str(self.stockcode) and hold_lst.get("CostPriceValid") == "1":
                        buy_stock_at_price = float(hold_lst.get("CostPrice"))
                        buy_stock_at_qty = int(hold_lst.get("Qty"))
                        self.run(buy_stock_at_price, 0, buy_stock_at_qty)                 # 开始自动交易

        else:                                                                             # 没有持有任何股票,或者此股票不在已持股票行列
            print "我还没有持有该股票：%s，开始购买。.." % self.stockcode
            (mairujia, mairushuliang) = self.fst_time_auto_buy()[1:]                      # 购买股票
            self.run(mairujia, 0, mairushuliang)                                          # 开始自动交易


    # buy_num:购买数量，单位：股，
    # buy_price_one, sell_price_one，摆盘中的数据
    def fst_time_auto_buy(self):

        fst_buy_fail = True
        sell_price_one = 0
        buy_price_one = 0
        buy_num = 0

        power_str, zcjz_str = self.ft.get_account_info()
        #print "pwer %s, zcjz:%s" % (power_str, zcjz_str)
        gear_info_lst = self.ft.get_stock_gear(1)           #真实环境

        while fst_buy_fail:
            for gear_info in gear_info_lst:
                sell_price_one = gear_info["SellPrice"]
                buy_price_one  = gear_info["BuyPrice"]

                buy_num = int(float(power_str)/(int(self.meishou) * int(sell_price_one)))
                if buy_num < 1:
                    print "当前资产净值(%.3f)太少，不够买一手！退出程序。" % (float(zcjz_str) / 1000)
                    sys.exit()

                '''第1次购买时，以现价/卖一价/设定价的最低值为交易价格，待商榷'''
                fst_bu_prc = min(int(sell_price_one), int(self.ft.get_cur_price()), float(self.fst_price)*1000)
                
                # def place_order(conn, order_side, order_type, price, qty, stock_code):
                # 美股中，参数三：“2”为普通下单
                if place_order(self.ft._conn, 0, 2, fst_bu_prc, buy_num, self.stockcode):
                    print "第1次交易%s，以卖一价格%0.3f买入%d手" % (self.stockcode, (float(fst_bu_prc))/1000, int(buy_num))
                else:
                    print "第1次购买失败，退出程序。"
                    sys.exit()
                
                fst_buy_fail = False

        return True, float(sell_price_one), buy_num   # 买入成功、买入价、买入数量

    def run(self, lst_time_exchange_price, lst_time_exchange_side, lst_time_exchange_num, i=2):

        #i = 2  # 交易次数
        #lst_time_exchange_price = self.fst_time_auto_buy()[1]
        #lst_time_exchange_side = 0
        #lst_time_exchange_num = self.fst_time_auto_buy()[3]
        print "start to run.."
        #if self.fst_time_auto_buy()[0]:
        while True:

            # 涨幅在2%-8%的时候，并且上一次交易为“买入”，卖出，并记录本次交易价格
            if self.controlline <= (float(self.ft.get_cur_price()) - float(lst_time_exchange_price))/float(lst_time_exchange_price) *100 < self.lowline \
                    and lst_time_exchange_side == 0:

                gear_info_lst_1 = self.ft.get_stock_gear(1)
                for gear_info in gear_info_lst_1:
                    buy_price_one_in_if = gear_info["BuyPrice"]
                    lst_time_exchange_side = lst_time_exchange_side^1

                    # 0 --买入， 1--卖出
                    if float(buy_price_one_in_if) >= float(buy_price_one_in_if):
                        place_order(self.ft._conn, lst_time_exchange_side, 0, buy_price_one_in_if, lst_time_exchange_num, self.stockcode)
                        print "第%s次交易，以买一价格%.3f卖出%d手。" % (i, ((float(buy_price_one_in_if))/1000), lst_time_exchange_num)
                        lst_time_exchange_price = buy_price_one_in_if
                        i += 1
                continue

            # 跌幅在2%-8%之间的时候，并且上一次交易为“卖出”，买入，并记录本次交易价格
            if self.controlline <= (float(lst_time_exchange_price) - float(self.ft.get_cur_price())) / float(lst_time_exchange_price)*100 < self.lowline\
                    and lst_time_exchange_side == 1:
                gear_info_lst_2 = self.ft.get_stock_gear(1)
                for gear_info in gear_info_lst_2:

                    sell_price_in_if = gear_info["SellPrice"]
                    lst_time_exchange_side = lst_time_exchange_side^1

                    # 0 --买入， 1--卖出
                    if float(sell_price_in_if) <= float(self.ft.get_cur_price()):
                        place_order(self.ft._conn, lst_time_exchange_side, 0, sell_price_in_if, lst_time_exchange_num, self.stockcode)
                        print "第%s次交易%s，以买一价格%0.3f买入%d手。" % (i, self.stockcode, (float(sell_price_in_if))/1000, lst_time_exchange_num)
                        lst_time_exchange_price = sell_price_in_if
                        i += 1
                continue

            # 买入后跌幅大于8%，或者买入后涨幅大于15%，全仓释放，不再交易
            if lst_time_exchange_side == 0 and \
                    ((float(lst_time_exchange_price) - float(self.ft.get_cur_price())) / float(lst_time_exchange_price) *100  >= 8 or
                        (float(self.ft.get_cur_price()) - float(lst_time_exchange_price)) / float(lst_time_exchange_price) *100 > 15):

                gear_info_lst_3 = self.ft.get_stock_gear(1)
                for gear_info in gear_info_lst_3:
                    buy_price_one_in_8_15 = gear_info["BuyPrice"]
                    lst_time_exchange_side = lst_time_exchange_side^1

                    # 0 --买入， 1--卖出
                    place_order(self.ft._conn, lst_time_exchange_side, 0, buy_price_one_in_8_15, lst_time_exchange_num, self.stockcode)
                    print "第%s次交易，以买一价格%0.3f卖出%d手,退出程序！" % (i, (float(buy_price_one_in_8_15))/1000, lst_time_exchange_num)
                    sys.exit()
#         else:
#             print "首次买入没有成功，退出。"
#             return

if __name__ == "__main__":
    stock = raw_input("股票代码(必须)：")
    meishou = raw_input("每手(必须)：")
    fst_price = raw_input("首次购买价(必须)：")
    num_shang = raw_input("上线(非必须)：")
    num_xia = raw_input("下线(非必须)：")
    controlline_num = raw_input("控制线(非必须)：")
    uplmt = 15 if num_shang == "" else num_shang
    lowlmt = 8 if num_xia == "" else num_xia
    controlline = 2 if controlline_num == "" else controlline_num
    print "股票代码：%s" % stock, "每手：%s" % meishou, "首次购买价：%s" %  fst_price, "上线：%s" % uplmt +'%', "下线：%s" %  lowlmt + '%'

    #connection = FT(stock)
    # print connection.get_cur_price()
    # print connection.get_account_info()
    #print connection.check_on_hold()
    # nok
    # print connection.get_stock_gear(1)

    DEAL_obj = DEAL(stock, lowlmt, uplmt, controlline, meishou, fst_price)
    DEAL_obj.trade()

