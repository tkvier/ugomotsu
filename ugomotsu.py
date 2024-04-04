import os
import sys
import json
import re
import requests
import tkinter as tk
from tkinter import filedialog
from tkinter import scrolledtext
from tkinter import messagebox
import hashlib
import concurrent.futures
#import datetime
#----------------------------------------
appver = "0.1.3"
config_json = os.path.join(os.path.dirname(sys.argv[0]),'config.json')
#----------------------------------------
class civitai_ModelAPI:
    def __init__(self):
        """
            civitai APIのjsonモデルデータを読み込み加工するクラス。
        """
        pass
    def get(self,url, modelid, verid):
        """
            civitai APIを取得し加工する
        Args:
            modelid (str): モデルID
            verid (str): バージョンID
        Attributes:
            model_basemodel (str): SD/SDXL version
            model_type (str): Modle type
            model_id (str): Modle ID
            model_name (str): Modle Name
            ver_id (str): Version ID
            ver_name (list): Modle Version
            model_description (list): About
            version_description (list): About this Version
            data_Hash (str): Modle Hash
        """
        def pathname_organization(target):
            """
                モデル名/バージョン名をファイルやフォルダに適した形式に変更する
            Args:
                target (str): モデル名
            Returns:
                str (str): ファイル名/フォルダ名に適してる形式に変換
            """
            target =  re.sub(r'[\\|/|:|*|?|"|<|>|\|]', '*', target)
            if len(target) > 40:
                if '*' in target and target.find('*') < 40 and target.find('*') > 5:
                    target = target[:target.find('*')]
                elif ' ' in target and target.find('-') < 40 and target.find('-') > 5:
                    target = target[:target.rfind(' ')]
                elif ' ' in target and target.find(' ') < 40 and target.find(' ') > 5:
                    target = target[:target.rfind(' ')]
                else:
                    target = target[:40]
            target = target.replace('*', ' ')
            target = target.replace("  ", " ")
            target = target.strip()
            return target

        # 
        civitaiapi = netio(url)
        if not civitaiapi.get():
            return False

        json_data = civitaiapi.response.json()
        self.model_id = json_data.get("id")
        self.model_name = json_data.get("name")
        self.model_fname = pathname_organization(self.model_name)
        self.model_description = json_data.get("description")
        self.model_type = json_data.get("type")
        self.nsfw = json_data.get("nsfw")
        self.tags = json_data.get("tags")
        self.disable_permits = ""
        self.permits_file = "This model permits users to "
        acuse = json_data.get("allowCommercialUse")
        if not json_data.get("allowNoCredit"):
            self.disable_permits += "クレジット無しでの使用\n"
            self.permits_file += "x"
        else:
            self.permits_file += "o"
        if not "Image" in acuse:
            self.disable_permits += "生成画像の商用利用\n"
            self.permits_file += "x"
        else:
            self.permits_file += "o"
        if not "Rent" in acuse:
            self.disable_permits += "モデルの商用利用\n"
            self.permits_file += "x"
        else:
            self.permits_file += "o"
        if not json_data.get("allowDerivatives"):
            self.disable_permits += "マージしたモデルの共有\n"
            self.permits_file += "x"
        else:
            self.permits_file += "o"
        if not "Sell" in acuse:
            self.disable_permits += "モデル(マージモデル)の販売\n"
            self.permits_file += "x"
        else:
            self.permits_file += "o"
        if not json_data.get("allowDifferentLicense"):
            self.disable_permits += "パーミッションの変更\n"
            self.permits_file += "x"
        else:
            self.permits_file += "o"
        self.permits_file += ".txt"
        if self.disable_permits == "":
            self.disable_permits = "無し\n"
        if  json_data.get("creator") == None:
            self.creator = "No Data"
        else:
            self.creator = json_data["creator"]["username"]
        verchkflg = False
        for item in json_data.get("modelVersions"):
            if item.get("id") == verid:
                verchkflg = True
                self.ver_id = item.get("id")
                self.ver_name = item.get("name")
                self.ver_fname = pathname_organization(self.ver_name)
                self.upload_date = item.get("createdAt")
                self.publish_date = item.get("publishedAt")
                if item.get("trainedWords") == None:
                    print("None")
                    self.trainedWords = False
                else:
                    self.trainedWords = '\n'.join(item.get("trainedWords"))
                    print(self.trainedWords)
                self.model_basemodel = item.get("baseModel")
                self.model_basemodeltype = item.get("baseModelType")
                self.stats = item.get("stats")
                self.downloadurl = item.get("downloadUrl")
                self.version_description = item.get("description")
                files = item.get("files")[0]
                self.metadata = files.get("metadata")
                self.hashes =  files.get("hashes")
                hoged = item.get("images")
                self.ImageURLs = [hoge.get('url') for hoge in hoged ]
        if verchkflg:
            return True
        else:
            return False
    def _remove_html_tags(self,input_string):
        """
            HTMLタグを除去する。
        Args:
            input_string (str): HTML形式(Unicode)の文字列。
        Returns:
            str (str): タグを除去した文字列。
        """
        tmp_string = input_string.replace('<p>', "\n")
        tmp_string = tmp_string.replace('</p>', "\n")
        tmp_string = tmp_string.replace('<br />', "\n")
        tmp_string = tmp_string.replace('<hr />', "\n")
        tmp_string = tmp_string.replace("&GT;", ">")
        tmp_string = tmp_string.replace("&LT;", "<")
        tmp_string = tmp_string.replace("\n\n", "\n")
        tag_pattern = re.compile(r"<.*?>")  # タグを表す正規表現
        return re.sub(tag_pattern, "", tmp_string)

    def _jp_datetime(self,datetime):
        """
            Civitai APIで取得した日付を加工
        Args:
            datetime (str): 日付 1234/12/12T12:12:12.123Z
        Returns:
            str (str): 日本語日時
        """
        datetime = datetime.split('.')[0]
        tmp_datetime = datetime.split('T')
        tmp_date = tmp_datetime[0].split('-')
        tmp_time = tmp_datetime[1].split(':')
        return f"{tmp_date[0]}年{tmp_date[1]}月{tmp_date[2]}日 {tmp_time[0]}時{tmp_time[1]}分{tmp_time[2]}秒"

class civitai_HashAPI:
    def __init__(self):
        """
            Hashを元にcivitai APIのjsonモデルデータを読み込み加工するクラス。
        Args:
            hash (str): モデルのhash
        Attributes:
            model_basemodel (str): SD/SDXL version
            model_type (str): Modle type
        """
        # Config API Address
    def get(self, url):
        gethash = netio(url)
        if gethash.get():
            json_data = gethash.response.json()
            self.model_id = json_data["modelId"]
            self.ver_id = json_data["id"]
            del gethash
            return True
        else:
            del gethash
            return False

class cmapi(civitai_ModelAPI):
    def get(self, modelid, verid):
        # Config API Address
        url = f"https://civitai.com/api/v1/models/{modelid}"
        return super().get(url, modelid, verid)

    def create_triggerfile(self,path,ow):
        """
            トリガーワードファイルを作成
        Args:
            folder (str):   作成するパス
        Returns:
            成功判断
        """
        fio = fileio()
        if not self.trainedWords:
            return False
        return fio.write(path,self.trainedWords,ow)

    def create_permitinfodata(self,folder,ow):
        """
            パーミッションファイルを作成
        Args:
            folder (str):   作成するパス
        Returns:
            成功判断
        """
        fio = fileio()
        path = os.path.join(folder,self.permits_file)
        if fio.chkpath(path):
            if ow != "ow":
                return False
        tmptext = f"< {self.model_name} の禁止事項 >\n※"
        tmptext += self._jp_datetime(self.upload_date)
        tmptext += "現在\n\n"
        tmptext += self.disable_permits
        return fio.write(path,tmptext,ow)

    # モデル情報
    def create_modelinfo(self,folder,ow):
        """
            モデル情報を作成
        Args:
            folder (str):   作成するパス
        Returns:
            成功判断
        """
        path = os.path.join(folder,f"About {self.model_fname}.txt")
        fio = fileio()
        if fio.chkpath(path):
            if ow != "ow":
                return False
        tmptext = "----------------------------------------\n" \
            "< モデル情報 >\n" \
            f"クリエイター: {self.creator}\n" \
            f"モデル名: {self.model_name}\n" \
            f"モデルID: {self.model_id}\n" \
            f"モデル種別: {self.model_type}\n" \
            f"Civitai URL: https://civitai.com/models/{self.model_id}\n" \
            "----------------------------------------\n" \
            "< 禁止事項 >\n"
        tmptext += self.disable_permits
        tmptext += "----------------------------------------\n"
        if self.model_description != None:
            tmptext += "< モデルについて >\n"
            tmptext += self._remove_html_tags(self.model_description)
        return fio.write(path,tmptext,ow)

    # バージョン情報
    def create_verinfo(self,folder,hash,ow):
        """
            バージョン情報を作成
        Args:
            folder (str):   作成するフォルダ
        Returns:
            成功判断
        """
        path = os.path.join(folder,f"About {self.model_fname} {self.ver_fname}.txt")
        fio = fileio()
        if fio.chkpath(path):
            if ow != "ow":
                return False
        tmptext = "----------------------------------------\n" \
            "< バージョン情報 >\n" \
            f"モデル名: {self.model_name}\n" \
            f"モデルバージョン: {self.ver_name}\n" \
            f"クリエイター: {self.creator}\n" \
            "----------------------------------------\n" \
            f"モデルID: {self.model_id}\n" \
            f"モデル種別: {self.model_type}\n" \
            f"ベースモデル: {self.model_basemodel}\n" \
            f"モデルタイプ: {self.model_basemodeltype}\n"
        if self.trainedWords != False:
            tmptext += "----------------------------------------\n" \
            f"トリガーワード\n{self.trainedWords}\n"
        tmptext += "----------------------------------------\n" \
            f"アップロード日: {self._jp_datetime(self.upload_date)}\n" \
            f"公開日: {self._jp_datetime(self.publish_date)}\n" \
            f"Hash: {hash}\n" \
            f"Civitai URL: https://civitai.com/models/{self.model_id}?modelVersionId={self.ver_id}\n"
        if self.downloadurl != None:
            tmptext += f"ダウンロードURL: {self.downloadurl}\n"
        tmptext += "----------------------------------------\n< 禁止事項 >\n"
        tmptext += self.disable_permits
        if self.version_description != None:
            tmptext += "----------------------------------------\n" \
                "< このバージョンについて >\n"
            tmptext += self._remove_html_tags(self.version_description)
        if self.model_description != None:
            tmptext += "----------------------------------------\n" \
                "< モデルについて >\n"
            tmptext += self._remove_html_tags(self.model_description)
        fio = fileio()
        return fio.write(path,tmptext,ow)

    def Create_InternetShortcutdata(self,folder):
        """
            インターネットショートカットを作成
        Args:
            folder (str):   ショートカットを作成するフォルダ
        Returns:
            成功判断
        """
        iscpath = os.path.join(folder, f"{self.model_fname} - Stable Diffusion {self.model_type} - Civitai.url")
        fio = fileio()
        if fio.chkpath(iscpath):
            return False
        tmptext = "[InternetShortcut]\n" \
            f"URL=https://civitai.com/models/{self.model_id}\n"
        fio = fileio()
        return fio.write(iscpath,tmptext)

    #サムネ画像DL設定
    def create_thumbnailcg(self,path):
        """
            サムネ画像を作成
        Args:
            path (str):   作成するフォルダパス
        Returns:
            成功判断
        """
        fio = fileio()
        cgfilenoext = os.path.splitext(path)[0]
        if fio.chkpath(f"{cgfilenoext}.preview.jpg","jpeg","png","webp"):
            return False
        if len(self.ImageURLs) < 1:
            return False
        imageURL = self.ImageURLs[0]
        thumbnail = netio(imageURL)
        if not thumbnail.get():
            return False
        cntype = thumbnail.response.headers.get('Content-Type').split('/')[1]
        if cntype == "jpeg":
            cntype = "jpg"
        imagepath = f"{cgfilenoext}.preview.{cntype}"
        return fio.write(imagepath,thumbnail.response.content,"wb")

    #作例画像DL設定
    def create_examplecg(self,folder):
        """
            作例画像を作成
        Args:
            folder (str):   作成するフォルダパス
        Returns:
            成功判断
        """
        fio = fileio()
        i = 0
        for imageURL in self.ImageURLs:
            cgfile = os.path.join(folder,os.path.basename(imageURL))
            if fio.chkpath(cgfile,"jpg","jpeg","png","webp"):
                continue
            imageURL = imageURL.replace('/width=450','')
            example = netio(imageURL)
            if not example.head():
                continue
            if example.response.headers.get("Content-Type") == None:
                imagepath = cgfile
            else:
                cntype = example.response.headers.get('Content-Type').split('/')[1]
                if cntype == "jpeg":
                    cntype = "jpg"
                imagepath = f"{os.path.splitext(cgfile)[0]}.{cntype}"
            if fio.chkpath(imagepath):
                continue
            if not example.get():
                continue
            if fio.write(imagepath, example.response.content,'wb'):
                i += 1
        return i

class chapi(civitai_HashAPI):
    '''
    APIのURLを提供する為のcivitai_HashAPIのサブクラス
    '''
    def get(self, hash):
        url = f'https://civitai.com/api/v1/model-versions/by-hash/{hash}'
        return super().get(url)
    
class cminfoConv:
    def __init__(self, InfoData):
        """
            cm-info のJsonのデータを加工するクラス。
        Args:
            InfoData (str): Json生データ。
        Attributes:
            model_id (str): Modle ID
            ver_id (str): Version ID
        """
        json_data = json.loads(InfoData)
        self.model_id = json_data["ModelId"]
        self.ver_id = json_data["VersionId"]
        self.hash = json_data["Hashes"]["SHA256"][:10]

class civitaiinfoConv:
    def __init__(self, InfoData):
        """
            cm-info のJsonのデータを加工するクラス。
        Args:
            InfoData (str): Json生データ。
        Attributes:
            model_id (str): Modle ID
            ver_id (str): Version ID
        """
        json_data = json.loads(InfoData)
        self.model_id = json_data["modelId"]
        self.ver_id = json_data["id"]
        self.hash = json_data["files"][0]["hashes"]["AutoV2"]

class netio:
    def __init__(self,url):
        '''
            ネットIO用クラス ※今はHEAD/GETのみ実装
            .response.status_code や response.content でデータ取得できる（そのまんま）

        '''
        self._url = url
    def head(self):
        try:
            self.response = requests.head(self._url)
            if self.response.status_code != 200:
                return False
        except requests.RequestException as e:
            return False
        return True
    def get(self):
        try:
            self.response = requests.get(self._url)
            if self.response.status_code != 200:
                return False
        except requests.RequestException as e:
            return False
        return True

class fileio:
    def __init__(self):
        self.filedata = None
        '''
            ファイルIO用クラス
            .response.status_code
        '''
    def chkpath(self,filepath,*exts):
        '''
        フォルダ内にファイルがあるかチェック
        引数２つ以降は拡張子を指定し、その拡張子の場合のチェックも行う
        Args:
            filepath (str): ファイル
            *exts (str): 調べる拡張子
        '''
        if os.path.isfile(filepath):
            return True
        if len(exts) == 0:
            return False
        for ext in exts:
            sfilepath = f"{os.path.splitext(filepath)[0]}.{ext}"
            if os.path.isfile(sfilepath):   
                return True
        return False

    def read(self,filepath,*mode):
        '''
        ファイルを読み込む
        Args:
            filepath (str): ファイル
            *mode (str): r:テキストモードで読み込む(デフォルト) / rb:バイナリモードで読み込む
        '''
        if not os.path.isfile(filepath):
            return False
        try:
            if 'rb' in mode:
                with open(filepath, 'rb') as iofile:
                    self.filedata = iofile.read()
            else:
                with open(filepath, 'r', encoding="utf-8") as iofile:
                    self.filedata = iofile.read()
        except OSError as e:
            return False
        else:
            return True
    def write(self,filepath,data,*mode):
        '''
        ファイルに書き込む
        Args:
            filepath (str): ファイル
            data (str): 書き込むデータ
            *mode (str): w:テキストモードで書き込む(デフォルト) / wb:バイナリモードで書き込む /ow 上書きモード
        '''
        if os.path.isfile(filepath):
            if not 'ow' in mode:
                return False
        try:
            if 'wb' in mode:
                with open(filepath, 'wb') as iofile:
                    iofile.write(data)
            else:
                with open(filepath, 'w', encoding="utf-8") as iofile:
                    iofile.write(data)
        except OSError as e:
            return False
        else:
            return True

    def json(self,filepath,jsondata):
        try:
            with open(filepath, 'w', encoding="utf-8") as iofile:
                json.dump(jsondata,iofile,indent=4)
        except OSError as e:
            return False
        else:
            return True      

def civitai_livechecker():
    """
        Civitaiに接続できるかチェック
    Args:
        無し
    Returns:
        true    :生きてる
        false   :死ーん
    """
    # Config API Address

    url = 'https://civitai.com/'
    livecheck = netio(url)
    return livecheck.head()

class modelFilesinfo:
    def __init__(self, path):
        """
            モデルのファイル一式を整頓し、フォルダ情報を提供する
        Args:
            path (str): 現在のモデルファイルがあるパス
        Attributes:
            modelpath (str):    モデルファイルのフルパス     a:\\ai\\sdxl\\hoge_v10.safetensor
            model_folder (str): モデルファイルあるフォルダ   a:\\ai\\sdxl\\
            modelfname (str):    モデル名                   hoge_v10
            modelext (str):     モデル拡張子               .safetensor
            modelspath (str):   モデルの降るパスの拡張子無し a:\\ai\\sdxl\\hoge_v10
            infofile (str):     cm-info.jp/civitai.info の有無 True/False
            ver_folder (str): バージョン情報があるフォルダ  
        """

        self.modelpath = path
        self.modelffolder = os.path.dirname(path)
        self.modelfile = os.path.basename(path)
        self.modelfname = os.path.splitext(self.modelfile)[0]
        self.modelext = os.path.splitext(self.modelfile)[1]
        self.modelspath = os.path.join(self.modelffolder,self.modelfname)
        self.cminfo = f"{self.modelspath}.cm-info.json"
        self.civitaiinfo = f"{self.modelspath}.civitai.info"
    def set_SHA256(self,sha256):
        self.sha256 = sha256
        self.hash = sha256[:10]
    def set_modelinfo(self, modelid, verid):
        self.modelid = modelid
        self.verid = verid
    def get_modelinfo(self,modelinfo):
        self.modelname = modelinfo.model_name
        self.modelfolder = os.path.join(self.modelffolder, modelinfo.model_fname)
        if not os.path.isdir(self.modelfolder):
            os.mkdir(self.modelfolder)
        self.vername = modelinfo.ver_name
        self.verfolder = os.path.join(self.modelfolder, modelinfo.ver_fname)
        if not os.path.isdir(self.verfolder):
            os.mkdir(self.verfolder)
    
#メインフォーム
def mainform(filelist):
    def execute():
        def processmsg(txt):
            process_txt.configure(state="normal")
            process_txt.insert(tk.END, f"\n{txt}")
            process_txt.see(tk.END)
            process_txt.configure(state="disabled")

        list_cnt = len(filelist)
        list_now = 0
        fio = fileio()
        nothumbnail = False
        noInternetShortcut = False
        notrigger = False
        nopermitininfo = False
        nomodelinfo = False
        noversioninfo = False
        noexamplecg = False
        overwrite = "w"
        if fio.read(config_json):
            config_data = json.loads(fio.filedata)
            nothumbnail = config_data.get('nothumbnail')
            noInternetShortcut = config_data.get('noInternetShortcut')
            notrigger = config_data.get('notrigger')
            nopermitininfo = config_data.get('nopermitininfo')
            nomodelinfo = config_data.get('nomodelinfo')
            noversioninfo = config_data.get('noversioninfo')
            noexamplecg = config_data.get('noexamplecg')
            if config_data.get('overwrite'):
                overwrite = "ow"
            else:
                overwrite = "w"
            processmsg("config.jsonを読み込み、初期設定を設定しました")
        processmsg(f"処理件数は{list_cnt}件です")
        if not civitai_livechecker():
            processmsg("Civitaiへのアクセスに失敗した為、処理を終了します")
            return
        else:
            processmsg("Civitaiへの接続を確認しました")

        for file in filelist:
            modelfinfo = modelFilesinfo(file)

            list_now += 1
            count_txt.set(f"{list_now}/{list_cnt}")
            status_txt.set(f"Process : {modelfinfo.modelfile}")
            processmsg(f"■□■□ {modelfinfo.modelfile} の処理を開始 □■□■")

            infofile = False
            if not fio.chkpath(modelfinfo.modelpath):
                processmsg(f"{modelfinfo.modelfile} が見つかりません。。このモデルの処理を終了します。")
                continue
            if fio.read(modelfinfo.cminfo):
                infofile = True
                # CM-info.jsonからデータを取得
                processmsg(f"{modelfinfo.cminfo}を解析")
                data_conv = cminfoConv(fio.filedata)
                modelfinfo.set_modelinfo(data_conv.model_id, data_conv.ver_id)
                modelfinfo.set_SHA256(data_conv.hash)
                del data_conv
            else:
                # civitai.infoからデータを取得
                if fio.read(modelfinfo.civitaiinfo):
                    infofile = True
                    processmsg(f"{modelfinfo.civitaiinfo} を解析")
                    data_conv = civitaiinfoConv(fio.filedata)
                    modelfinfo.set_modelinfo(data_conv.model_id, data_conv.ver_id)
                    modelfinfo.set_SHA256(data_conv.hash)
                else:
                    #SHA256ファイルがある場合はそれを使用
                    if fio.read(f"{modelfinfo.modelspath}.sha256"):
                        modelfinfo.set_SHA256(fio.filedata)
                        processmsg("SHA256ファイルを読み込みました")
                    else:
                        # hash(SHA256)を計算
                        processmsg(f"{modelfinfo.modelfile}を読み込み")
                        if not fio.read(modelfinfo.modelpath,'rb'):
                            processmsg(f"{modelfinfo.modelfile}の読み込みに失敗しました。このモデルの処理を終了します。")
                            continue
                        processmsg(f"SHA256を計算中…(時間がかかります)")
                        SHA256 = hashlib.sha256(fio.filedata).hexdigest()
                        modelfinfo.set_SHA256(SHA256)
                        processmsg(f"計算終了 {modelfinfo.sha256}")
                        #SHA256ファイルを作成
                        fio.write(f"{modelfinfo.modelspath}.sha256",SHA256)
                    #civitaiのHash APIでモデル情報を取得
                    mhash = chapi()
                    if not mhash.get(modelfinfo.sha256):
                        processmsg(f"Civitaiからハッシュに対応するモデルの取得に失敗した為、{modelfinfo.modelfile} の処理を終了します")
                        del mhash
                        continue
                    modelfinfo.set_modelinfo(mhash.model_id, mhash.ver_id)
                    del mhash
                    processmsg("CivitaiのHash APIからモデルIDとバージョンIDを取得しました")
            processmsg(f"モデルID:{modelfinfo.modelid}/バージョンID:{modelfinfo.verid}のモデルデータをCivitaiから取得します")
            civitaiapi = cmapi()
            if not civitaiapi.get(modelfinfo.modelid, modelfinfo.verid):
                processmsg(f"Civitaiからモデルデータの取得に失敗した為、{modelfinfo.modelfile} の処理を終了します")
                continue
            processmsg("モデルデータを取得しました")
            modelfinfo.get_modelinfo(civitaiapi)
            # トリガーワード作成
            if not notrigger:
                if civitaiapi.create_triggerfile(f"{modelfinfo.modelspath}.txt",overwrite):
                    processmsg("トリガーワードファイルを作成しました")
            # パーミッションファイルの作成
            if not nopermitininfo:
                if civitaiapi.create_permitinfodata(modelfinfo.modelfolder,overwrite):
                    processmsg("パーミッション情報ファイルを作成しました")
            # モデル情報を作成の作成
            if not nomodelinfo:
                if civitaiapi.create_modelinfo(modelfinfo.modelfolder,overwrite):
                    processmsg("モデル情報ファイルを作成しました")
            # バージョン情報の作成
            if not noversioninfo:
                if civitaiapi.create_verinfo(modelfinfo.verfolder,modelfinfo.hash,overwrite):
                    processmsg("バージョン情報ファイルを作成しました")
            # インターネットショートカットの作成
            if not noInternetShortcut:
                if civitaiapi.Create_InternetShortcutdata(modelfinfo.modelfolder):
                    processmsg("インターネットショートカットを作成しました")
            # サムネイルを作成
            if not nothumbnail:
                if civitaiapi.create_thumbnailcg(modelfinfo.modelpath):
                    processmsg("サムネイル画像を作成しました")
            # 作例画像の作成
            if not noexamplecg:
                processmsg("作例画像を取得します（時間がかかる場合があります）")
                processmsg(f"{civitaiapi.create_examplecg(modelfinfo.verfolder)}件の作例画像を作成しました")
            processmsg(f"{modelfinfo.modelfile} の処理が終了しました")
            
        del fio
        status_txt.set("Complete the process")
        processmsg("全ての処理が完了しました")

# UI
    main_root = tk.Tk()
    main_root.title(f"Version {appver}")
    main_root.geometry("640x400")

    #ステータスバー
    status_frame = tk.Frame(main_root, bd = 1, relief = tk.SUNKEN)
    status_frame.pack(side = tk.BOTTOM, fill = tk.X, padx = 5, pady = 5)

    status_txt = tk.StringVar()
    status_txt.set("Ready")
    status_label = tk.Label(status_frame, textvariable = status_txt)
    status_label.pack(side = tk.LEFT, padx = 2, pady = 2)
    count_txt = tk.StringVar()
    count_txt.set("0/0")
    status_label = tk.Label(status_frame, textvariable = count_txt)
    status_label.pack(side = tk.RIGHT, padx = 2, pady = 2)
    # 処理リスト
    process_txt = scrolledtext.ScrolledText(main_root, width = 999,height = 999, relief = tk.SUNKEN, bd = 2)
    process_txt.pack(anchor = tk.NW,padx = 5)
    process_txt.insert(0., "処理を開始します。")
    process_txt.configure(state="disabled")

    #マルチスレッド
    executor = concurrent.futures.ThreadPoolExecutor(1)
    executor.submit(execute)
    #シングルスレッド(テスト用)
##    main_root.after(1,execute)

    main_root.mainloop()

# コンフィグフォーム
def configform():
    def saveconfig():
        fio = fileio()
        dic =dict(
            nothumbnail = nothumbnail_var.get(),
            noInternetShortcut = noInternetShortcut_var.get(),
            notrigger = notrigger_var.get(),
            nopermitininfo = nopermitininfo_var.get(),
            nomodelinfo = nomodelinfo_var.get(),
            noversioninfo = noversioninfo_var.get(),
            noexamplecg = noexamplecg_var.get(),
            overwrite = overwrite_var.get()
        )
        if fio.json(config_json,dic):
            messagebox.showinfo("設定の保存",f"{config_json}\n設定を正常に保存しました。")
        else:
            messagebox.showerror("設定の保存", "設定を正常に保存出来ませんでした。")

    info_root = tk.Tk()
    info_root.title(f"Version {appver}")
    info_root.geometry("380x400")
    msg_label = tk.Label(info_root, text = 
        "このプログラムは画像AIモデルのデータをCivitaiから取得するプログラムです。\n"
        "cm-info.jsonやcivirai.infoがあればそれらを使用し時短します。\n\n"
        "■□■□ 使い方 ■□■□\n\n"
        "AIモデルファイルを実行ファイルに関連付けて起動するか、\n"
        "実行ファイルにAIモデルファイルをドラッグ＆ドロップしてください\n\n"
        "■□■□ 設定 ■□■□"
    )
    msg_label.pack(pady = 10)

    nothumbnail_var = tk.BooleanVar()
    noInternetShortcut_var = tk.BooleanVar()
    notrigger_var = tk.BooleanVar()
    nopermitininfo_var = tk.BooleanVar()
    nomodelinfo_var = tk.BooleanVar()
    noversioninfo_var = tk.BooleanVar()
    noexamplecg_var = tk.BooleanVar()
    overwrite_var = tk.BooleanVar()
    fio = fileio()
    if fio.read(config_json):
        config_data = json.loads(fio.filedata)
        nothumbnail_var.set(config_data.get('nothumbnail'))
        noInternetShortcut_var.set(config_data.get('noInternetShortcut'))
        if config_data.get('notrigger') == None:
            notrigger_var.set(False)
        else:
            notrigger_var.set(config_data.get('notrigger'))
        nopermitininfo_var.set(config_data.get('nopermitininfo'))
        nomodelinfo_var.set(config_data.get('nomodelinfo'))
        noversioninfo_var.set(config_data.get('noversioninfo'))
        noexamplecg_var.set(config_data.get('noexamplecg'))
        if config_data.get('overwrite') == None:
            overwrite_var.set(False)
        else:
            overwrite_var.set(config_data.get('overwrite'))

    # チェックボックス
    notrigger_Checkbutton = tk.Checkbutton(info_root, variable = notrigger_var, text = "トリガーワードのファイルを作成しない")
    notrigger_Checkbutton.pack(anchor=tk.NW,padx=20)
    nopermitininfo_Checkbutton = tk.Checkbutton(info_root, variable = nopermitininfo_var, text = "パーミッションファイルを作成しない")
    nopermitininfo_Checkbutton.pack(anchor=tk.NW,padx=20)
    nomodelinfo_Checkbutton = tk.Checkbutton(info_root, variable = nomodelinfo_var, text = "モデルの情報ファイルを作成しない")
    nomodelinfo_Checkbutton.pack(anchor=tk.NW,padx=20)
    noversioninfo_Checkbutton = tk.Checkbutton(info_root, variable = noversioninfo_var, text = "モデルのバージョン情報ファイルを作成しない")
    noversioninfo_Checkbutton.pack(anchor=tk.NW,padx=20)
    noInternetShortcut_Checkbutton = tk.Checkbutton(info_root, variable = noInternetShortcut_var, text = "インターネットショートカットを作成しない")
    noInternetShortcut_Checkbutton.pack(anchor=tk.NW,padx=20)
    nothumbnail_Checkbutton = tk.Checkbutton(info_root, variable = nothumbnail_var, text = "サムネイル画像を作成しない")
    nothumbnail_Checkbutton.pack(anchor=tk.NW,padx=20)
    noexamplecg_Checkbutton = tk.Checkbutton(info_root, variable = noexamplecg_var, text = "モデルの作例画像を保存しない")
    noexamplecg_Checkbutton.pack(anchor=tk.NW,padx=20)
    overwrite_Checkbutton = tk.Checkbutton(info_root, variable = overwrite_var, text = "上書きモードで保存（テキストのみ）")
    overwrite_Checkbutton.pack(anchor=tk.NW,padx=20)

    btnfrm = tk.Frame(info_root)
    btnfrm.pack()
    save_button = tk.Button(btnfrm, text = "設定を保存", command = saveconfig)
    save_button.pack(ipadx = 15, ipady = 2,side = tk.LEFT)
    close_button = tk.Button(btnfrm, text = "閉じる", command = info_root.destroy)
    close_button.pack(ipadx = 15, ipady = 2,side = tk.LEFT)
    info_root.mainloop()
# 引数処理
def addtasklist(argvs):
    flist = []
    for argv in argvs:
        if os.path.isdir(argv):
            #フォルダなので中身を再帰処理
            hoge = [os.path.join(argv,dirlist) for dirlist in os.listdir(argv)]
            rlist = addtasklist(hoge)
            if not rlist == []:
                flist.extend(rlist)
        elif os.path.isfile(argv):
            #AIファイルなら登録
            if argv.endswith(".safetensors") or argv.endswith(".ckpt"):
                flist.append(argv)
    return flist

def main():
    if len(sys.argv) > 1:
        files = sys.argv
        files.pop(0)
        hoge = addtasklist(files)
        mainform(hoge)
    else:
        configform()

if __name__ == "__main__":
    main()
