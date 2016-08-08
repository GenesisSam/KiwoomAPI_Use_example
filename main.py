# -*- coding: utf-8 -*-

import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *

USER_INFO_TYPE = {
    "ACC_CNT": "ACCOUNT_CNT",   # 전체계좌 갯수
    "ALL_ACC": "ACCNO",         # 전체 계좌 ; 으로 구분
    "UID": "USER_ID",           # 사용자 ID
    "UNAME": "USER_NAME"        # 사용자 이름
}

class kiwoomWidget(QAxWidget):

    def __init__(self):
        super().__init__()
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        self.OnEventConnect[int].connect(self._OnEventConnect)
        self.OnReceiveTrData[str, str, str, str, str, int, str, str, str].connect(self._OnReceiveTrData)
        self.OnReceiveMsg[str, str, str, str].connect(self._OnReceiveMsg)
        self.OnReceiveChejanData[str, int, str].connect(self._OnReceiveChejanData)
        self.loginCheck = False

        # 커맨드상 종료 방지.(async라서 프로세스가 미리 종료 됩니다.)
        self.login_event_loop = QEventLoop()

    def _OnReceiveMsg(self, ScrNo, RQName, TrCode, Msg):
        print("ReceiveMsg, scrNo= %s, RQName= %s, TrCode=%s,\nMsg=%s" % (ScrNo, RQName, TrCode, Msg))

    '''
    Gubun- 0:주문체결 통보, 1:잔고통보, 2: 특이신호
    '''
    def _OnReceiveChejanData(self, Gubun, ItemCnt, FidList):
        print("ChejanData, Gubun=%s, ItemCnt=%d, FidList=%s" % (Gubun, ItemCnt, FidList))
        flist = FidList.split(';')
        for fid in flist:
            result = self.dynamicCall("GetChejanData(int)", int(fid))
            if fid == 912 and reuslt == "체결":
                print("#### 체결되었습니다. ####")
            print(result)
        print("----------------------\n\n")

    def _OnReceiveTrData(self, ScrNo, RQName, TrCode, RecordName, PrevNext, DataLength, ErrorCode, Message, SplmMsg):
        if RQName == "Request1":
            v = [self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", TrCode, "", RQName, 0, "종목명").strip(),
                 self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", TrCode, "", RQName, 0, "현재가").strip(),
                 self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", TrCode, "", RQName, 0, "거래량").strip(),]

            print(str(v))

        elif RQName == "Request2":      # 내 계좌내 있는 보유종목 조회
            va = {"cash": self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", TrCode, "", RQName, 0, "D+2추정예수금").strip(),
                  "stocks": []}
            idx = self.dynamicCall("GetDataCount(QString)", RQName)
            for i in range(0, idx):
                v = {"name": self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", TrCode, "", RQName, i, "종목명").strip(),
                     "qty": self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", TrCode, "", RQName, i, "보유수량").strip(),
                     "price": self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", TrCode, "", RQName, i, "평균단가").strip()}

                va["stocks"].append(v)
            print(va)

        elif RQName == "RQ_1":
            print("RQ_1\n")
        self.login_event_loop.exit()

    def _OnEventConnect(self, errCode):
        if errCode == 0:
            self.loginCheck = True
            self.login_event_loop.exit()
            print("connected")
        else:
            self.loginCheck = False
            print("disconnected")

    # login windows open
    def CommConnect(self):
        import time
        self.dynamicCall("CommConnect()")
        self.login_event_loop.exec_()

    # 전체 계좌 정보를 반환합니다.
    def getMyAllAccount(self):
        print("getall my account")
        if self.loginCheck:
            ret = self.dynamicCall("GetLoginInfo(QString)", "ACCNO")
            ret = [x for x in ret.split(';') if x]
            return ret
        return ""

    # 현재가 조회용 함수
    def getValue(self, scode=None):
        print("현재가 조회")
        if self.loginCheck:
            if type(scode) != str:
                scode = str(scode)

            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", scode)
            error = self.dynamicCall("CommRqData(QString, Qstring, int, Qstring)", "Request1", "opt10001", 0, "0101")

            self.login_event_loop.exec_()

    # 계좌 정보 조회
    def getPort(self, acc_num, pwdInputType="00"):
        print("계좌정보 조회")

        if self.loginCheck:
            if type(acc_num) != str:
                acc_num = str(acc_num)

            self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", acc_num)
            self.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "")     # 메모리상 변수로 지정하면 "계좌비밀번호입력창에서 값을 넣어도 타인계좌로 뜸"
            self.dynamicCall("SetInputValue(QString, QString)", "상장폐지조회구분", 0)
            self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", pwdInputType)

            ac_cnt = 0

            while True:
                error = self.dynamicCall("CommRqData(QString, Qstring, int, Qstring)", "Request2", "opw00004", 0, "0346")

                print(self.error_catch(error))
                if error == -201:
                    print("실패 %d회" % ac_cnt)
                    if ac_cnt >= 5:
                        break
                    self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", acc_num)
                    ret = self.dynamicCall("KOA_Functions(QString, QString)", "ShowAccountWindow", "")
                    ac_cnt = ac_cnt+1
                elif error == 0:
                    self.login_event_loop.exec_()
                    break
                else:
                    break

    '''
        ordType : 1: 신규매수, 2:신규매도, 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정
        00:지정가, 03:시장가, 05:조건부지정가, 06:최유리지정가, 07:최우선지정가, 10: 지정가IOC, 13:시장가IOC, 16:최유리IOC, 20:지정가FOK, 23:시장가FOK,
        26:최유리FOK, 61: 장전시간외종가, 62:시간외단일가, 81:장후시간외종가
        ※ 시장가, 최유리지정가, 최우선지정가, 시장가IOC, 최유리IOC, 시장가FOK, 최유리FOK, 장전시간외, 장후시간외 주문시 주문가격을 입력하지 않습니다.
    '''
    def doOrder(self, accNum, ordType, sCode, nQty, nPrice, sHogaGb):
        print("주문")

        if type(accNum) != str:
            accNum = str(accNum)
        error = -999

        ac_cnt = 0

        while True:
            error = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)", ["RQ_1", "0101", accNum, int(ordType), str(sCode), int(nQty), int(nPrice), str(sHogaGb), ""])
            print(self.error_catch(error))

            if error == -301:
                print("실패 %d회" % ac_cnt)
                if ac_cnt >= 5:
                    # 5회 비밀번호 입력 실패시 프로그램 종료.
                    break
                ret = self.dynamicCall("KOA_Functions(QString, QString)", "ShowAccountWindow", "")
                ac_cnt = ac_cnt + 1
            elif error == 0:
                self.login_event_loop.exec_()
                break
            else:
                break


    def error_catch(self, errorNum):
        errMsg = {
            "0": "정상처리",
            "-100": "사용자정보교환에 실패하였습니다.\n잠시후 다시 시작하여 주세요.",
            "-101": "키움 API 서버 접속 실패",
            "-102": "버전처리가 실패하였습니다.",
            "-200": "시세조회 과부하",
            "-201": "REQUEST_INPUT_st Failed",
            "-202": "요청 전문 작성 실패",
            "-300": "주문 입력값 오류",
            "-301": "계좌비밀번호를 입력하십시오",
            "-302": "타인계좌는 사용할 수 없습니다.",
            "-303": "주문가격이 20억원을 초과합니다.",
            "-304": "주문가격은 50억원을 초과할 수 없습니다.",
            "-305": "주문수량이 총발행주수의 1%를 초과합니다.",
            "-306": "주문수량은 총발행주수의 3%를 초과할 수 없습니다.",
            "-999": "프로세스 동작 실패."
        }
        if type(errorNum) != str:
            errorNum = str(errorNum)
        try:
            return errMsg[errorNum]
        except KeyError:
            return "Unknown error"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    kw = kiwoomWidget()
    kw.CommConnect()

    acc = kw.getMyAllAccount()
    print(acc)

    kw.getValue("000020")       # 현재가 조회
    kw.getPort(acc[0])          # 보유종목 가져오기

    """
    주문 함수 예제
    kw.doOrder(acc[0], 2, '036620', 18, 0, "03")
    """

    print("\n\n==============================\n\n")
    # 실시간 체결 정보를 receive하기위해 프로세스를 계속 살려 주는 용도입니다.
    kw.login_event_loop.exec_()