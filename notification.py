import requests
from bs4 import BeautifulSoup
import os
import numpy as np
import os
from linebot import LineBotApi
from linebot.models import TextSendMessage
import psycopg2
from psycopg2 import extras

LINE_NOTIFY_TOKEN = os.environ['LINE_NOTIFY_TOKEN'] #環境変数からLINEのトークンコードを取得
line_bot_api = LineBotApi(LINE_NOTIFY_TOKEN)
DATABASE_URL = os.environ['DATABASE_URL']   #環境変数からHeroku PostgerSQLのURLを取得


#メイン実行関数
def main():
    old_list = outputlastlog()  #前回の商品リストをold_listに代入
    new_list = mklist2()    #販売中の商品リストをnew_listに代入
    lineNewStock(NewStock(new_list,old_list))   #old_listになく、new_listにある商品を探してLineに送る
    linePriceChange(PriceChange(new_list,old_list)) #old_list, new_listのどちらにもあるが価格が異なる商品を見つけLineに送る
    inputlastlog(new_list)  #new_listの商品を保存する


#新たに入荷した商品の情報をLineで送る
def lineNewStock(Lmail):
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
        if text_out != []:
            message_contents = text_title + text_out    #message_contensの内容をtext_title + text_outにする
            line_bot_api.broadcast(TextSendMessage(message_contents)) #Lineにmessage_contentsの内容を送信する


#価格が変更された商品の情報をLineで送る
def linePriceChange(Lmail):
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
        if text_out != []:
            message_contents = text_title + text_out    #message_contensの内容をtext_title + text_outにする
            line_bot_api.broadcast(TextSendMessage(message_contents)) #Lineにmessage_contentsの内容を送信する


#webサイトから商品情報(商品名, 価格 , 販売状況, URL)を取得し、配列に加えて返す
def mklist2():
    base_url = 'https://www.e-okashi.shop/shopbrand/sale/page'  #目的のWebサイトのURL
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
        url_part = 'https://www.e-okashi.shop' #参照先urlの一部分
        names = soup.select('.name a') #商品名を取得
        prices = soup.select('.price em') #価格を取得
        salestatus = soup.select('p.quantity > span') #販売状況を取得
        for (name, price, sstatus) in zip(names ,prices, salestatus): #names, prices, salestatusの要素をname, price, sstatusに同時に繰り返し代入していく
            if sstatus.text  != '売り切れ': #salestatusが売り切れではない時実行
                result.append([ name.text, price.text, url_part + name.get('href') ]) #result配列にnames, prices, salestatusの要素を追加
        num += 1 #ページ番号を+1する
    return result #mklist2の結果としてresultの内容を返す


#取得した商品リストをPostgres(last_logs)上に保存する
def inputlastlog(new_list):
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as curs:
            curs.execute("DELETE FROM last_logs") #前回保存した要素をすべて削除する
            extras.execute_values(curs, "INSERT INTO last_logs(Item_name, price, URL) VALUES %s",new_list) #newlistのすべての要素を保存する


#PostgreSQL(last_logs)から前回の商品リストを保存する
def outputlastlog():
    with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT * FROM last_logs") #現在保存されているlast_logsの内容を取得する
                return curs.fetchall() #outputlastlogの結果として取得したlast_logsの内容を返す


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


if __name__ == "__main__":
    main()