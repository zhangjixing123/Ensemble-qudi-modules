# set the parameters
from time import sleep , time
import pywinusb.hid as hid

# basic func
teVendorId  = 0x168C
# teLucidDesktopId  = 0x6002  # Use this for Lucid Desktop - 6GHz
# teLucidPortableId = 0x6081  # Use this for Lucid Portable - 6GHz + 1 Channel
teLucidBenchtopIdLS1292B = 0x1202  # Use this for Lucid Benchtop - 12GHz + 2 Channels LS1292B
teLucidBenchtopIdLS3082B = 0x3002  # Use this for Lucid Benchtop - 3GHz + 2 Channels LS3082B

BUFFER_SIZE = 256

class test():
    def __init__(self):
        self.text = None

    def readData(self, data):
        """
        HIDデバイスからデータを受信した際に呼び出されるコールバック関数。
        受信したバイトデータを文字列に変換し、self.textに格納する。
        """
        text = ""
        # 受信データが空でないことを確認
        if data:
            for c in data:
                # NULLバイト(0)は無視
                if c != 0:
                    text += chr(c)
            # 意味のある文字列が構築された場合のみself.textを更新
            if text.strip():
                self.text = text.strip() # 前後の空白や改行を削除
        return None

    def send_scpi_cmd(self, device, scpi_cmd):
        """
        SCPIコマンドをデバイスに送信する（応答は待たない）。
        例: ':OUTP1 ON'
        """
        if not device:
            print("No device provided")
            return
        
        device.open()
        
        # 送信バッファの準備
        buffer = [0x00] * BUFFER_SIZE
        sendData = bytearray(scpi_cmd, 'utf-8')
        sendData_len = len(sendData)
        for i in range(sendData_len):
            buffer[i + 3] = sendData[i]
            
        # レポートを送信
        device.send_output_report(buffer)
        
        # コマンドが処理されるのを少し待つ
        sleep(0.1)
        
        device.close()

    def query_scpi_cmd(self, device, scpi_cmd, timeout=2.0):
        """
        SCPIクエリを送信し、デバイスからの応答を待って返す。
        例: '*IDN?'
        """
        if not device:
            print("No device provided")
            return None
        
        device.open()
        
        # 応答を格納する変数をリセット
        self.text = None
        
        # 応答を処理するコールバック関数を設定
        device.set_raw_data_handler(self.readData)
        
        # 送信バッファの準備
        buffer = [0x00] * BUFFER_SIZE
        sendData = bytearray(scpi_cmd, 'utf-8')
        sendData_len = len(sendData)
        for i in range(sendData_len):
            buffer[i + 3] = sendData[i]
        
        # レポート（クエリ）を送信
        device.send_output_report(buffer)
        
        # 応答が来るまでタイムアウト付きで待機
        start_time = time()
        while self.text is None:
            sleep(0.05) # CPU負荷を下げるための短い待機
            if time() - start_time > timeout:
                print(f"エラー: {timeout}秒以内に応答がありませんでした。")
                device.close()
                return None
        
        device.close()
        return self.text


# MW parameter
# basic func
# teVendorId  = 0x168C
# teLucidBenchtopIdLS1292B = 0x1202  # Use this for Lucid Benchtop - 12GHz + 2 Channels LS1292B
# teLucidBenchtopIdLS3082B = 0x3002  # Use this for Lucid Benchtop - 3GHz + 2 Channels LS3082B

def controlTabor(freq, pow, dev, teVendorId, teLucidBenchtopId):
    # connect device
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    ''' Reset the device and test the connection '''
    a = test()
    a.send_scpi_cmd(lucid_device, '*CLS')
    a.send_scpi_cmd(lucid_device, '*RST')
    print(f"接続成功: {a.query_scpi_cmd(lucid_device,'*IDN?')}") # IDNクエリで接続確認
    
    print("設定値:", freq, pow, dev)
    
    """ set the parameters of sweep mode"""
    freq1 = int(freq[0]*1e6)
    pow1 = pow[0]
    freq2 = int(freq[1]*1e6)
    pow2 = pow[1]

    # --- チャンネル1の設定 ---
    print("\n--- チャンネル1を設定中 ---")
    a.send_scpi_cmd(lucid_device, ':INST 1\n')      # select the channel
    a.send_scpi_cmd(lucid_device, 'OUTP ON\n')
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq1))
    a.send_scpi_cmd(lucid_device, 'POWer {}\n'.format(pow1))
    a.send_scpi_cmd(lucid_device, ':FM ON')
    a.send_scpi_cmd(lucid_device, ':FM:SOUR EXT')
    a.send_scpi_cmd(lucid_device, ':FM:DEV {}\n'.format(dev))

    # --- 【追加】チャンネル1の設定値をクエリして確認 ---
    # デバイスが設定を処理するのを少し待つ
    sleep(0.5) 
    ch1_freq_actual = float(a.query_scpi_cmd(lucid_device, ':FREQuency?'))
    ch1_pow_actual = float(a.query_scpi_cmd(lucid_device, ':POWer?'))
    ch1_fm_dev_actual = float(a.query_scpi_cmd(lucid_device, ':FM:DEV?'))
    print("【確認】チャンネル1 周波数:", ch1_freq_actual / 1e6, "MHz")
    print("【確認】チャンネル1 パワー:", ch1_pow_actual, "dBm")
    print("【確認】チャンネル1 FM偏移:", ch1_fm_dev_actual, "Hz")


    # --- チャンネル2の設定 ---
    print("\n--- チャンネル2を設定中 ---")
    sleep(1) # チャンネル切り替えの間に少し待機
    a.send_scpi_cmd(lucid_device, ':INST 2\n')      # select the channel
    a.send_scpi_cmd(lucid_device, 'OUTP ON\n')
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq2))
    a.send_scpi_cmd(lucid_device, 'POWer {}\n'.format(pow2))
    a.send_scpi_cmd(lucid_device, ':FM ON')
    a.send_scpi_cmd(lucid_device, ':FM:SOUR EXT')
    a.send_scpi_cmd(lucid_device, ':FM:DEV {}\n'.format(dev))

    # --- 【追加】チャンネル2の設定値をクエリして確認 ---
    sleep(0.5)
    ch2_freq_actual = float(a.query_scpi_cmd(lucid_device, ':FREQuency?'))
    ch2_pow_actual = float(a.query_scpi_cmd(lucid_device, ':POWer?'))
    ch2_fm_dev_actual = float(a.query_scpi_cmd(lucid_device, ':FM:DEV?'))
    print("【確認】チャンネル2 周波数:", ch2_freq_actual / 1e6, "MHz")
    print("【確認】チャンネル2 パワー:", ch2_pow_actual, "dBm")
    print("【確認】チャンネル2 FM偏移:", ch2_fm_dev_actual, "Hz")

    sleep(2)
    print(f'ch1 set to {freq1}')
    print(f'ch2 set to {freq2}')
    
def closecontrolTabor(teVendorId, teLucidBenchtopId):
    # connect device
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    ''' Reset the device and test the connection '''
    a = test()
    """ set the parameters of sweep mode"""
    a.send_scpi_cmd(lucid_device, ':INST 1\n')  # select the channel
    a.send_scpi_cmd(lucid_device, 'OUTP OFF\n')
    a.send_scpi_cmd(lucid_device, ':INST 2\n')  # select the channel
    a.send_scpi_cmd(lucid_device, 'OUTP OFF\n')
    a.send_scpi_cmd(lucid_device, '*CLS')
    #a.send_scpi_cmd(lucid_device, '*RST')
    print(f'ch1 closed')
    print(f'ch2 closed')



def controlTabor1st(freq, pow, dev, teVendorId, teLucidBenchtopId):
    # connect device
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    ''' Reset the device and test the connection '''
    a = test()
    a.send_scpi_cmd(lucid_device, '*CLS')
    a.send_scpi_cmd(lucid_device, '*RST')
    a.send_scpi_cmd(lucid_device,'*IDN?')
    print(freq, pow, dev)
    """ set the parameters of sweep mode"""
    freq1 = int(freq[0]*1e6)
    pow1 = pow[0]
    freq2 = int(freq[1]*1e6)
    pow2 = pow[1]

    # set the parameters of single freq output Channel 1
    # a.send_scpi_cmd(lucid_device, ':FM:DEV?')

    a.send_scpi_cmd(lucid_device, ':INST 1\n')  # select the channel
    a.send_scpi_cmd(lucid_device, 'OUTP ON\n')
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq1))
    a.send_scpi_cmd(lucid_device, 'POWer {}\n'.format(pow1))
    a.send_scpi_cmd(lucid_device, ':FM ON')
    a.send_scpi_cmd(lucid_device, ':FM:SOUR EXT')
    a.send_scpi_cmd(lucid_device, ':FM:DEV {}\n'.format(dev))


    sleep(2)
    a.send_scpi_cmd(lucid_device, ':INST 2\n')  # select the channel
    a.send_scpi_cmd(lucid_device, 'OUTP OFF\n')
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq2))
    a.send_scpi_cmd(lucid_device, 'POWer {}\n'.format(pow2))

    sleep(2)

    
def controlTabor2nd(teVendorId, teLucidBenchtopId):
    # connect device
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    ''' Reset the device and test the connection '''
    a = test()
    a.send_scpi_cmd(lucid_device, '*CLS')
    #a.send_scpi_cmd(lucid_device, '*RST')
    a.send_scpi_cmd(lucid_device,'*IDN?')
    """ set the parameters of sweep mode"""

    # set the parameters of single freq output Channel 1
    # a.send_scpi_cmd(lucid_device, ':FM:DEV?')
    sleep(2)
    a.send_scpi_cmd(lucid_device, ':INST 2\n')  # select the channel

    # a.send_scpi_cmd(lucid_device, ':INST 2\n')  # select the channel
    # a.send_scpi_cmd(lucid_device, 'OUTP ON\n')


def controlTaborCW(teVendorId, teLucidBenchtopId):
    # connect device
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    ''' Reset the device and test the connection '''
    a = test()

    # set the parameters of single freq output Channel 1
    # a.send_scpi_cmd(lucid_device, ':FM:DEV?')

    a.send_scpi_cmd(lucid_device, ':INST 1\n')  # select the channel
    a.send_scpi_cmd(lucid_device, 'OUTP OFF\n')
    a.send_scpi_cmd(lucid_device, ':FM OFF')

    sleep(2)

    a.send_scpi_cmd(lucid_device, ':INST 2\n')  # select the channel
    a.send_scpi_cmd(lucid_device, 'OUTP OFF\n')
    a.send_scpi_cmd(lucid_device, ':FM OFF')

    sleep(2)

def setTaborCW_Output(freq, pow, teVendorId, teLucidBenchtopId):
    """
    変調（FM）をオフにし、指定された周波数とパワーで
    CW（連続波）を両チャンネルから出力する。
    """
    # connect device
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    ''' Reset the device and test the connection '''
    a = test()
    a.send_scpi_cmd(lucid_device, '*CLS')
    a.send_scpi_cmd(lucid_device, '*RST')
    print(f"接続成功: {a.query_scpi_cmd(lucid_device,'*IDN?')}") # IDNクエリで接続確認
    
    print("設定値 (CWモード):", freq, pow)
    
    """ set the parameters of CW mode"""
    freq1 = int(freq)
    pow1 = pow

    # --- チャンネル1の設定 (CW) ---
    print("\n--- チャンネル1を設定中 (CW) ---")
    a.send_scpi_cmd(lucid_device, ':INST 2\n')      # チャンネル1を選択
    a.send_scpi_cmd(lucid_device, ':FM OFF\n')      # ★FM変調をオフ
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq1))
    a.send_scpi_cmd(lucid_device, 'POWer {}\n'.format(pow1))
    a.send_scpi_cmd(lucid_device, 'OUTP ON\n')      # ★出力をオン

    # --- 【確認】チャンネル1の設定値をクエリ ---
    #sleep(0.5) 
    #ch1_freq_actual = float(a.query_scpi_cmd(lucid_device, ':FREQuency?'))
    #ch1_pow_actual = float(a.query_scpi_cmd(lucid_device, ':POWer?'))
    #ch1_fm_stat = a.query_scpi_cmd(lucid_device, ':FM:STAT?') # FMの状態を確認
    #print("【確認】チャンネル1 周波数:", ch1_freq_actual, "Hz")
    #print("【確認】チャンネル1 パワー:", ch1_pow_actual, "dBm")
    #print("【確認】チャンネル1 FM状態:", ch1_fm_stat) # 'OFF'が返るはず


    #sleep(2)
    print(f'ch1 (CW) set to {freq1} Hz')

def setTaborCW_Output_2ch(freq_m, pow_m,freq_p,pow_p, teVendorId, teLucidBenchtopId):
    """
    変調（FM）をオフにし、指定された周波数とパワーで
    CW（連続波）を両チャンネルから出力する。
    """
    # connect device
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    ''' Reset the device and test the connection '''
    a = test()
    a.send_scpi_cmd(lucid_device, '*CLS')
    a.send_scpi_cmd(lucid_device, '*RST')
    print(f"接続成功: {a.query_scpi_cmd(lucid_device,'*IDN?')}") # IDNクエリで接続確認
    
    print("設定値 (CWモード):", freq_m, pow_m)
    
    """ set the parameters of CW mode"""
    freq1 = int(freq_m)
    pow1 = pow_m
    freq2 = int(freq_p)
    pow2 = pow_p

    # --- チャンネル1の設定 (CW) ---
    print("\n--- チャンネル1を設定中 (CW) ---")
    a.send_scpi_cmd(lucid_device, ':INST 2\n')      # チャンネルmigiを選択
    a.send_scpi_cmd(lucid_device, ':FM OFF\n')      # ★FM変調をオフ
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq1))
    a.send_scpi_cmd(lucid_device, 'POWer {}\n'.format(pow1))
    a.send_scpi_cmd(lucid_device, 'OUTP ON\n')      # ★出力をオン

    a.send_scpi_cmd(lucid_device, ':INST 1\n')      # チャンネルhidariを選択
    a.send_scpi_cmd(lucid_device, ':FM OFF\n')      # ★FM変調をオフ
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq2))
    a.send_scpi_cmd(lucid_device, 'POWer {}\n'.format(pow2))
    a.send_scpi_cmd(lucid_device, 'OUTP ON\n')      # ★出力をオン

    print(f'ch1 (CW) set to {freq2} Hz')
    print(f'ch2 (CW) set to {freq1} Hz')

def setfreq(freq, teVendorId, teLucidBenchtopId):
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    a = test()
    freq1 = int(freq)
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq1))
    print(f'ch1 (CW) set to {freq1} Hz')

def setfreq_2ch(freq_m, freq_p, teVendorId, teLucidBenchtopId):
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    a = test()
    freq1 = int(freq_m)
    freq2 = int(freq_p)
    a.send_scpi_cmd(lucid_device, ':INST 2\n') 
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq1))
    a.send_scpi_cmd(lucid_device, ':INST 1\n') 
    a.send_scpi_cmd(lucid_device, 'FREQuency {}\n'.format(freq2))
    print(f'ch1 (CW) set to {freq2} Hz')
    print(f'ch2 (CW) set to {freq1} Hz')

def setoff(teVendorId, teLucidBenchtopId):
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    a = test()
    a.send_scpi_cmd(lucid_device, ':INST 2\n')      # チャンネル1を選択
    a.send_scpi_cmd(lucid_device, 'OUTP OFF\n')      # ★出力をオン
    print(f'ch1 off')

def setoff_2ch(teVendorId, teLucidBenchtopId):
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    a = test()
    a.send_scpi_cmd(lucid_device, ':INST 1\n')      # チャンネル1を選択
    a.send_scpi_cmd(lucid_device, 'OUTP OFF\n')      # ★出力をオン
    a.send_scpi_cmd(lucid_device, ':INST 2\n')      # チャンネル1を選択
    a.send_scpi_cmd(lucid_device, 'OUTP OFF\n')      # ★出力をオン
    print(f'ch1&ch2 off')

def set_IQ(teVendorId, teLucidBenchtopId):
    lucid_device = hid.HidDeviceFilter(
        vendor_id=teVendorId, product_id=teLucidBenchtopId).get_devices()[0]
    a = test()
    
    # --- 修正点 ---
    # すべてのコマンドに \n を追加
    a.send_scpi_cmd(lucid_device, ':INST 2\n')      # チャンネル1を選択
    a.send_scpi_cmd(lucid_device, ':PM OFF\n')       # PM変調をON
    
    # コマンドを 'SOURC' ではなく 'SOUR' にする
    #a.send_scpi_cmd(lucid_device, ':PM:SOURC EXT\n')
 
    # クエリも 'SOUR' を使い、末尾に \n を追加
    #response = a.query_scpi_cmd(lucid_device, ':PM:SOURC?\n')
    #print(f"PM:SOUR? {response}") # 'EXT' が返ってくるはず
    
    # （参考）PMがONになっているか確認
    #response_on = a.query_scpi_cmd(lucid_device, ':PM?\n')
    #print(f"PM? {response_on}") # 'ON' (または '1') が返るはず