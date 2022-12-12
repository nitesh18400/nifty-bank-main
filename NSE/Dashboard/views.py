import requests
import json
import math
import datetime

from collections import deque
from django.shortcuts import render
import pytz

sess = requests.Session()
cookies = dict()

ce_sum_list = deque()
pe_sum_list = deque()
diffrence_list = deque()
pcrlist = deque()

# Method to get nearest strikes
def round_nearest(x,num=50): return int(math.ceil(float(x)/num)*num)
def nearest_strike_bnf(x): return round_nearest(x,100)
def nearest_strike_nf(x): return round_nearest(x,50)

# Urls for fetching Data
url_oc      = "https://www.nseindia.com/option-chain"
url_bnf     = 'https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY'
url_nf      = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
url_indices = "https://www.nseindia.com/api/allIndices"


# Headers
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
            'accept-language': 'en,gu;q=0.9,hi;q=0.8',
            'accept-encoding': 'gzip, deflate, br'}

# Local methods
def set_cookie():
    request = sess.get(url_oc, headers=headers, timeout=5)
    cookies = dict(request.cookies)

def get_data(url):
    set_cookie()
    response = sess.get(url, headers=headers, timeout=5, cookies=cookies)
    if(response.status_code==401):
        set_cookie()
        response = sess.get(url_nf, headers=headers, timeout=5, cookies=cookies)
    if(response.status_code==200):
        return response.text
    return ""

def set_header():
    global bnf_ul
    global nf_ul
    global bnf_nearest
    global nf_nearest
    response_text = get_data(url_indices)
    data = json.loads(response_text)
    for index in data["data"]:
        if index["index"]=="NIFTY 50":
            nf_ul = index["last"]
            print("nifty")
        if index["index"]=="NIFTY BANK":
            bnf_ul = index["last"]
            print("banknifty")
    bnf_nearest=nearest_strike_bnf(bnf_ul)
    nf_nearest=nearest_strike_nf(nf_ul)


# Fetching CE and PE data based on Nearest Expiry Date
def CE_PE_Data_Extract(num,step,nearest,url):
    strike = nearest - (step*num)
    start_strike = nearest - (step*num)
    response_text = get_data(url)
    data = json.loads(response_text)
    currExpiryDate = data["records"]["expiryDates"][0]
    cesm = 0 
    pesm = 0
    
    price_info = []
    
    for item in data['records']['data']:
        if item["expiryDate"] == currExpiryDate:
            if item["strikePrice"] == strike and item["strikePrice"] < start_strike+(step*num*2):
                cesm += item["CE"]["changeinOpenInterest"]
                pesm += item["PE"]["changeinOpenInterest"]
                

                #print(strCyan(str(item["strikePrice"])) + strGreen(" CE ") + "[ " + strBold(str(item["CE"]["openInterest"]).rjust(10," ")) + " ]" + strRed(" PE ")+"[ " + strBold(str(item["PE"]["openInterest"]).rjust(10," ")) + " ]")
                price_info.append([data["records"]["expiryDates"][0], str(item["strikePrice"]), str(item["CE"]["changeinOpenInterest"]), str(item["PE"]["changeinOpenInterest"])])
                strike = strike + step
    
    # print(f"CE SUM OF CHNG IN OI = {cesm}")
    # print(f"PE SUM OF CHNG IN OI = {pesm}")
    # print(f"DIFFERENCE PC = {pesm-cesm}")
    # print(f"PCR = {round(pesm/cesm,5)}")
    
    
    
    if not ce_sum_list or ce_sum_list[-1] != round(cesm,5):
        ce_sum_list.append(round(cesm,5))
        if len(ce_sum_list)>10:
            ce_sum_list.popleft()
            

    if not pe_sum_list or pe_sum_list[-1] != round(pesm,5):
        pe_sum_list.append(round(pesm,5))
        if len(pe_sum_list)>10:
            pe_sum_list.popleft()
            

    if not diffrence_list or diffrence_list[-1] != round(pesm-cesm,5):
        diffrence_list.append(round(pesm-cesm,5))
        if len(diffrence_list)>10:
            diffrence_list.popleft()
            
    
    if not pcrlist or pcrlist[-1] != round(pesm/cesm,5):
        pcrlist.append(round(pesm/cesm,5))
        if len(pcrlist)>10:
            pcrlist.popleft()
    
    return {"Price_Info": price_info, "Ce_Sum": list(ce_sum_list), "Pe_Sum": list(pe_sum_list), "Difference": list(diffrence_list), "PCR": list(pcrlist)}


def home(request):
    
    set_header()
    
    data = CE_PE_Data_Extract(10,100,bnf_nearest,url_bnf)
    
    data["c_time"] = datetime.datetime.now(tz = pytz.timezone('Asia/Kolkata')).strftime("%d/%m/%y %H:%M:%S")
    data["bnf_ul"] = bnf_ul
    data["bnf_nearest"] = bnf_nearest
    print(data["c_time"])
    
    return render(request, "home.html", context=data)
