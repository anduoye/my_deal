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
        req_param = {'Market':'1','StockCode':'%s' % str(self._code)}  #Market:港股，StockCode:股票代码
        data = send_req_and_get_rsp(self._conn, 1001, req_param, 1)    #获取当前股票基础信息
        real_price = int(data["Cur"])
        return real_price

    def get_stock_gear(self, get_gear_num):
        req_param = {"Market":"1",'StockCode':'%s' % str(self._code),"GetGearNum":str(get_gear_num)}
        analyzed_rsps = send_req_and_get_rsp(self._conn,1002,req_param,1)
        '''
            {
            "GearArr":[{"BuyOrder":"1","BuyPrice":"135300","BuyVol":"3400","SellOrder":"2","SellPrice":"135400","SellVol":"27000"},
                       {"BuyOrder":"5","BuyPrice":"135200","BuyVol":"64000","SellOrder":"5","SellPrice":"135500","SellVol":"70200"},
                       {"BuyOrder":"20","BuyPrice":"135100","BuyVol":"108300","SellOrder":"9","SellPrice":"135600","SellVol":"142300"}],
            "Market":"1",
            "StockCode":"00700"},
            "Version":"1"
            }
        '''
        dic_gear_info_lst = analyzed_rsps["GearArr"]
        if dic_gear_info_lst is None:
            print "获取买卖档口错误"
            return

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

        # def send_req_and_get_rsp(conn, protocol_code, req_param, protocol_version): #发包
        account_info_rsp = send_req_and_get_rsp(self._conn, 6007, req_param, 1)
        return account_info_rsp["Power"], account_info_rsp["ZCJZ"]

    def check_on_hold(self):
        req_param = {"Cookie":"123456","EnvType":"0"}
        # {"Protocol":"6009","ReqParam":{"Cookie":"123123","EnvType":"0"},"Version":"1"}
        on_hold_dict = send_req_and_get_rsp(self._conn, 6009, req_param, 1)
        on_holded_stock_lst = on_hold_dict["HKPositionArr"]

        return on_holded_stock_lst


# stcokcode: 股票代码
# lowline: 止损线
# upline: 止盈线
# controlline: 交易触发线
class DEAL():
    def __init__(self, stockcode, lowline, upline, controlline, meishou):
        self._stockcode = stockcode
        self._lowline = lowline
        self._upline = upline
        self._controlline = controlline
        self._meishou = meishou
        self._ft = FT(stockcode)

    # 检查持仓列表
    # 没有持仓此股票，则buy
    # 有持仓此股票，则检查cookie确定sell或buy
    def i_have_hold(self):
        i_have_lst = []
        hold_lsts = self._ft.check_on_hold()

        if not hold_lsts:               # 没有持有股票
            self.fst_time_auto_buy()         # 购买股票
        else:
            hold_stock_lst = [hold_lst["StockCode"] for hold_lst in hold_lsts]  # 已经持有的股票代码，列表
            if str(self._stockcode) in hold_stock_lst:
                pass # check_price_to_deal()
            else:
                pass

    # buy_num:购买数量，单位：股，
    # buy_price_one, sell_price_one，摆盘中的数据
    def fst_time_auto_buy(self):

        fst_buy_fail = True
        sell_price_one = 0
        buy_price_one = 0
        buy_num = 0

        power_str, zcjz_str = self._ft.get_account_info()
        print "pwer %s, zcjz:%s" % (power_str, zcjz_str)
        gear_info_lst = self._ft.get_stock_gear(3)   #真实环境

        while fst_buy_fail:
            for gear_info in gear_info_lst:
                sell_price_one = gear_info["SellPrice"]
                buy_price_one  = gear_info["BuyPrice"]

                buy_num = int(float(power_str)/(int(self._meishou) * sell_price_one) )
                if buy_num < 1:
                    print "当前资产净值(%o.3f)太少，不够买一手！退出。" % float(zcjz_str) / 1000
                    return False

                if int(sell_price_one) >= int(self._ft.get_cur_price()):
                    if place_order(0, 0, sell_price_one, buy_num, self._stockcode):
                        print "首次购买，以卖一价格%0.3f买入%d手" % ((float(sell_price_one))/1000, int(buy_num))

                        fst_buy_fail = False

        return True, float(sell_price_one), float(buy_price_one), buy_num

    def run(self):

        i = 2  # 交易次数
        lst_time_exchange_price = self.fst_time_auto_buy()[1]
        lst_time_exchange_side = 0

        lst_time_exchange_num = self.fst_time_auto_buy()[3]

        print "start to run.."
        if self.fst_time_auto_buy()[0]:
            while True:

                # 涨幅在2%-8%的时候，并且上一次交易为“买入”，卖出，并记录本次交易价格
                if self._controlline < (self._ft.get_cur_price() - lst_time_exchange_price)/lst_time_exchange_price<self._lowline \
                        and lst_time_exchange_side == 0:

                    gear_info_lst_1 = self._ft.get_stock_gear(3)
                    for gear_info in gear_info_lst_1:
                        buy_price_one_in_if = gear_info["BuyPrice"]

                        lst_time_exchange_side = lst_time_exchange_side^1

                        # 0 --买入， 1--卖出
                        if place_order(lst_time_exchange_side, 0, buy_price_one_in_if, lst_time_exchange_num, self._stockcode):
                            print "第%s次交易，以买一价格%0.3f卖出%d手。" % (i, (float(buy_price_one_in_if))/1000, lst_time_exchange_num)
                            lst_time_exchange_price = buy_price_one_in_if
                            i += 1
                    continue

                # 跌幅在2%-8%之间的时候，并且上一次交易为“卖出”，买入，并记录本次交易价格
                if self._controlline <= (lst_time_exchange_price - self._ft.get_cur_price())/lst_time_exchange_price<self._lowline\
                        and lst_time_exchange_side == 1:
                    gear_info_lst_2 = self._ft.get_stock_gear(3)
                    for gear_info in gear_info_lst_2:

                        sell_price_in_if = gear_info["SellPrice"]
                        lst_time_exchange_side = lst_time_exchange_side^1

                        # 0 --买入， 1--卖出
                        if place_order(lst_time_exchange_side, 0, sell_price_in_if, lst_time_exchange_num, self._stockcode):
                            print "第%s次交易，以买一价格%0.3f买入%d手。" % (i, (float(sell_price_in_if))/1000, lst_time_exchange_num)
                            lst_time_exchange_price = sell_price_in_if
                            i += 1
                    continue

                # 买入后跌幅大于8%，或者买入后涨幅大于15%，全仓释放，不再交易
                if lst_time_exchange_side == 0 and \
                        ((lst_time_exchange_price - self._ft.get_cur_price()) / lst_time_exchange_price > 8 or
                            (self._ft.get_cur_price() - lst_time_exchange_price) / lst_time_exchange_price > 15):

                    gear_info_lst_3 = self._ft.get_stock_gear(3)
                    for gear_info in gear_info_lst_3:
                        buy_price_one_in_8_15 = gear_info["BuyPrice"]

                        lst_time_exchange_side = lst_time_exchange_side^1

                        # 0 --买入， 1--卖出
                        if place_order(lst_time_exchange_side, 0, buy_price_one_in_8_15, lst_time_exchange_num, self._stockcode):
                            print "第%s次交易，以买一价格%0.3f卖出%d手,退出程序！" % (i, (float(buy_price_one_in_8_15))/1000, lst_time_exchange_num)
                            sys.exit()
        else:
            print "首次买入没有成功，退出。"
            return

if __name__ == "__main__":
    stock = raw_input("股票代码(必须)：")
    meishou = raw_input("每手(必须)：")
    num_shang = raw_input("上线(非必须)：")
    num_xia = raw_input("下线(非必须)：")
    controlline_num = raw_input("控制线(非必须)：")
    uplmt = 15 if num_shang == "" else num_shang
    lowlmt = 8 if num_xia == "" else num_xia
    controlline = 2 if controlline_num == "" else controlline_num
    print "股票代码：%s" % stock, "每手：%s" % meishou, "上线：%s" % uplmt +'%', "下线：%s" %  lowlmt + '%'

    #connection = FT(stock)
    # print connection.get_cur_price()
    # print connection.get_account_info()
    #print connection.check_on_hold()
    # nok
    # print connection.get_stock_gear(1)

    DEAL_obj = DEAL(stock, lowlmt, uplmt, controlline, meishou)
    DEAL_obj.run()

