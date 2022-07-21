import requests
from bs4 import BeautifulSoup
import numpy as np
import os
from linebot import LineBotApi
from linebot.models import TextSendMessage
import psycopg2
from psycopg2 import extras
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def pagescroll(driver):
    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        sleep(2.5)
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

#新たに入荷した商品の情報をLineで送る
def lineNewStock(Lmail, line_bot_api):
    if Lmail !=[]:  #Lmailが空(新たに商品の入荷がない)場合に実行
        text_out = ''   #text_outを初期化する
        text_title = '★ 商品が追加されました ★\n──────────────────\n\n'   #送信するメッセージのタイトルを設定
        text1 = '{}\n{}\n{}\n\n──────────────────\n\n'  #送信するメッセージに「商品名 + 改行 + URL + 改行 + 【価格】 + 改行 + 区切り線」を追加するための準備
        for i in range(len(Lmail)): #追加された商品数と同じ回数実行
            text_out += text1.format(Lmail[i][0], Lmail[i][2], Lmail[i][1]) #text1の{}部分に順番に「商品名」「URL」「価格」を代入し、追加する
            if (i+1) % 10 == 0: #10商品ごとにメセージを分割する(Lineで一度に遅れるメッセージは5000までのため)
                message_contents = text_title + text_out    #message_contensの内容をtext_title + text_outにする
                line_bot_api.broadcast(TextSendMessage(message_contents)) #Lineにmessage_contentsの内容を送信する
                text_out = ''   #一度商品リストを初期化する(一度10商品を送信していた場合、その情報を削除するため)
        if len(text_out) != 0:
            message_contents = text_title + text_out    #message_contensの内容をtext_title + text_outにする
            line_bot_api.broadcast(TextSendMessage(message_contents)) #Lineにmessage_contentsの内容を送信する


#価格が変更された商品の情報をLineで送る
def linePriceChange(Lmail, line_bot_api):
    if Lmail !=[]:  #Lmailが空でない(すでにある商品の価格が変更された)場合に実行
        text_out = ''   #text_outを初期化する
        text_title = '● 商品の価格が変更されました ●\n──────────────────\n\n'   #送信するメッセージのタイトルを設定
        text1 = '{}\n{}\n{} \n↓↓↓↓↓↓\n{}\n\n──────────────────\n\n' #送信するメッセージに「商品名 + 改行 + URL + 改行 + 以前の価格 + 改行 + ↓↓↓↓↓↓ + 新しい価格 +区切り線」を追加するための準備
        for i in range(len(Lmail)): #価格が変更された商品数と同じ回数実行
            text_out += text1.format(Lmail[i][0], Lmail[i][3], Lmail[i][1], Lmail[i][2])    #text1の{}部分に順番に「商品名」「URL」「以前の価格」「新しい価格」を代入し、追加する
            if (i+1) % 10 == 0: #10商品ごとにメセージを分割する(Lineで一度に遅れるメッセージは5000までのため)
                message_contents = text_title + text_out    #message_contensの内容をtext_title + text_outにする
                line_bot_api.broadcast(TextSendMessage(message_contents)) #Lineにmessage_contentsの内容を送信する
                text_out = ''   #一度商品リストを初期化する(一度10商品を送信していた場合、その情報を削除するため)
        if len(text_out) != 0:
            message_contents = text_title + text_out    #message_contensの内容をtext_title + text_outにする
            line_bot_api.broadcast(TextSendMessage(message_contents)) #Lineにmessage_contentsの内容を送信する


#webサイトにログインし、商品情報(商品名, 価格 , 販売状況, URL)を取得し、配列に加えて返す
def mklistlogin(url, url_part, tn_name, tn_price, tn_sstatus, soldout_text):
    result = [] #結果出力用配列
    names = [0] 
    prices = [0]
    options = Options()
    options.add_argument('--headless')
    # ブラウザを起動する
    driver = webdriver.Chrome(options=options)
    driver.get(url + url_part)
    Alert(driver).accept()
    search = driver.find_element_by_name('id')
    search.send_keys(MAIL_ADDRESS)
    search = driver.find_element_by_name('passwd')
    search.send_keys(LOGIN_PASSWORD)
    search = driver.find_element(by=By.CLASS_NAME, value='btn')
    search.click()
    sleep(20)
    html = driver.page_source.encode('utf-8') #URLのWebサイトからHTMLを取得
    soup = BeautifulSoup(html, 'html.parser')
    names = soup.select(tn_name)
    prices = soup.select(tn_price)
    salestatus = soup.select(tn_sstatus)
    for (name, price, sstatus) in zip(names ,prices, salestatus):
        if sstatus.text  != soldout_text:
            result.append([ name.text, price.text, url + name.get('href') ])
    driver.close()
    return result

#webサイトから商品情報(商品名, 価格 , 販売状況, URL)を取得し、配列に加えて返す
def mklist(base_url, url_part, tn_name, tn_price, tn_sstasus, soldout_text):
    num = 1 #ページ番号
    b = 0 #商品数
    result = [] #結果出力用配列
    names = [0] 
    prices = [0]
    while len(names) != 0:  #全ページ実行
    #while num <= 10: #テスト用指定ページ数実行
        url = base_url + str(num) #商品URLにページ番号を追加する
        res = requests.get(url) #URLのWebサイトからHTMLを取得
        soup = BeautifulSoup(res.text, 'html.parser')
        names = soup.select(tn_name)
        prices = soup.select(tn_price)
        salestatus = soup.select(tn_sstasus)
        for (name, price, sstatus) in zip(names ,prices, salestatus):
            if sstatus.text  != soldout_text:
                result.append([ name.text, price.text, url_part + name.get('href') ])
        num += 1
    return result

#動的なwebサイトにアクセスし、商品情報(商品名, 価格 , URL)を取得し、配列に加えて返す
def mklist_move(url, tn_name, tn_price, tn_link):
    result = [] #結果出力用配列
    names = [0] 
    prices = [0]
    options = Options()
    options.add_argument('--headless')
    # ブラウザを起動する
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    sleep(5)
    driver.refresh()
    sleep(5)
    pagescroll(driver)
    sleep(5)
    html = driver.page_source.encode('utf-8') #URLのWebサイトからHTMLを取得
    soup = BeautifulSoup(html, "html.parser")
    names = soup.select(tn_name)
    prices = soup.select(tn_price)
    links = soup.select(tn_link)
    for (name, price, link) in zip(names, prices, links):
        result.append([name.text, price.text, link.get('href')])
    driver.close()
    return result

#取得した商品リストをPostgres(last_logs)上に保存する
def inputlastlog(new_list, tablename):
    dcommand = "DELETE FROM " + tablename
    iicommand = "INSERT INTO " + tablename + "(Item_name, price, URL) VALUES %s"
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as curs:
            curs.execute(dcommand)
            extras.execute_values(curs, iicommand ,new_list)


#PostgreSQL(last_logs)から前回の商品リストを保存する
def outputlastlog(tablename):
    scommand = "SELECT * FROM " + tablename
    with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as curs:
                curs.execute(scommand)
                return curs.fetchall()


#新たに入荷された商品の情報を出力
def NewStock(nums_new, nums_old):
    nums1 = np.array(nums_new)
    nums2 = np.array(nums_old)
    ans=[]
    for i in range(len(nums1)):
        n=0
        for j in range(len(nums2)):
            if (nums1[i, 0] == nums2[j, 0]):
                n=1
        if n == 0:
            ans.append(nums_new[i])
    return ans

#価格が変更された既存の商品の情報を出力
def PriceChange(nums_new, nums_old):
    nums1 = np.array(nums_new)
    nums2 = np.array(nums_old)
    ans=[]
    for i in range(len(nums1)):
        n=0
        for j in range(len(nums2)):
            if (nums1[i, 0] == nums2[j, 0]):
                if (nums1[i, 1] != nums2[j, 1]):
                    ans.append([nums_new[i][0], nums_old[j][1], nums_new[i][1], nums_new[i][2]])
    return ans

#共通のデータベースURL
DATABASE_URL =  'postgres://plbijhwxmpznhe:0acf2a14fc1e731d5363065fb95c72150cf5956e5ee422a4f3b7a9291c515f9d@ec2-18-215-8-186.compute-1.amazonaws.com:5432/d4dmu5250ut37f'  #環境変数からHeroku PostgerSQLのURLを取得

#メールアドレス
#MAIL_ADDRESS = os.environ['MAIL_ADDRESS']
#LOGIN_PASSWORD = os.environ['LOGIN_PASSWORD']

#いいお菓子ドットショップ 訳あり品・処分品・アウトレット大特価市
baseurl_okashi = 'https://www.e-okashi.shop/shopbrand/sale/page'
url_part_okashi = 'https://www.e-okashi.shop'
tn_name_okashi= '.name a'
tn_price_okashi = '.price em'
tn_sstatus_okashi = 'p.quantity > span'
table_okashi =  "last_logs"
soldout_text_okashi = '売り切れ'
#LINE_NOTIFY_TOKEN_okashi = os.environ['LINE_NOTIFY_TOKEN']
#line_bot_api_okashi = LineBotApi(LINE_NOTIFY_TOKEN_okashi)

#いいお菓子ドットショップ　先行セール【会員限定】
url_okashi_mo = 'https://www.e-okashi.shop'
url_part_okashi_mo = '/shopbrand/member/'
tn_name_okasi_mo= '.name a'
tn_price_okashi_mo = '.price em'
tn_sstatus_okashi_mo = 'p.quantity > span'
table_okashi_mo =  "mo_last_logs"
soldout_text_okashi_mo = '売り切れ'
#LINE_NOTIFY_TOKEN_okashi_mo =  os.environ['LINE_NOTIFY_TOKEN2']
#line_bot_api_okashi_mo = LineBotApi(LINE_NOTIFY_TOKEN_okashi_mo)

#ビューティーアウトレットショップ「セルレ」公式通販
baseurl_celule = 'https://paypaymall.yahoo.co.jp/store/celuleonlineshop/category/a1f9newite/'
tn_name_celule = 'p.ListItem_title'
tn_price_celule = 'span.ListItem_price'
tn_link_celule = 'div.ListItem > a'
table_celule =  "celule_last_logs"
LINE_NOTIFY_TOKEN_celule = 'AJahyKkQVxXJLGQAUwiiX5gKP0cErSc5Qf0lPDDPOLc4w6NFlL/W6gct0EnpGJRuAFniDc9w79/vwIY1l121LXLh/ipauO2c70p5KW1RHDWVoOBjKbfZUS49MQEJjANZzg5u/UKCje40BH3F46g49QdB04t89/1O/w1cDnyilFU='
line_bot_api_celule = LineBotApi(LINE_NOTIFY_TOKEN_celule)

#メイン実行関数
def main(custom, tablename, line_bot_api):
    old_list = outputlastlog(tablename)  #前回の商品リストをold_listに代入
    new_list = custom    #販売中の商品リストをnew_listに代入
    lineNewStock(NewStock(new_list,old_list), line_bot_api)   #old_listになく、new_listにある商品を探してLineに送る
    linePriceChange(PriceChange(new_list,old_list), line_bot_api) #old_list, new_listのどちらにもあるが価格が異なる商品を見つけLineに送る
    inputlastlog(new_list ,tablename)  #new_listの商品を保存する

if __name__ == "__main__":
    #いいお菓子ドットショップ　先行セール【会員限定】
    #main(mklist(baseurl_okashi, url_part_okashi, tn_name_okashi, tn_price_okashi, tn_sstatus_okashi, soldout_text_okashi), table_okashi ,line_bot_api_okashi)
    #main(mklistlogin(url_okashi_mo, url_part_okashi_mo, tn_name_okasi_mo, tn_price_okashi_mo, tn_sstatus_okashi_mo, soldout_text_okashi_mo), table_okashi_mo, line_bot_api_okashi_mo)
    main(mklist_move(baseurl_celule, tn_name_celule, tn_price_celule, tn_link_celule), table_celule, line_bot_api_celule)