import struct
from sys import byteorder
import jellyfish
from time import localtime, strftime
import sys

class m4a_parser:
    def __init__(self, data_in):
        self.output=self.parse_m4a(data_in)
        self.structure_error_flag =0
        self.abnormal_structure_flag=0
        self.abnormal_time_flag =0
        self.wrong_time_flag =0 
        self.iphone_flag=0
        self.structure_error_flag =0
        self.iphone_abnormal_flag=0
        self.iphone_normal_flag=0
        self.iphone_but_abnormal_flag = 0
        self.temper_flag=0
        self.multimedia_meta_flag=0 
        self.multimedia_meta_error_flag =0
        self.manipulated_score=100
        self.log=""
        self.score_log=""
    def timeto_hfs(self, time):
        t=time
        local=localtime((t-2082844800))
        time_format='%Y-%m-%d %H:%M:%S'
        result= strftime(time_format, local)
        return result

    def ascii_check(self, input):
        count = 0
        for i in range(0,len(input)):
            if input[i] > 0x40:
                if input[i] < 0x7F:
                    count +=1
        if count == len(input):
            return 1
        else:
            return 0

    def key_extraction(self,a,level,key_list):
        if len(key_list) <= level:
            key_list.append([])
        for key in a.keys():
            if len(a[key]) >1:
                key_list[level].append(key)
                self.key_extraction(a[key][1],level+1,key_list)
            else:
                key_list[level].append(key)


    
    def structure_comp(self,a,b):
        if a==-1 or b == -1:
            # print("INVALID FILE FORMAT")
            self.structure_error_flag =1
            self.log = self.log+"container 구조가 비정상적입니다. "
            return 0
        a_result=[]
        self.key_extraction(a,0,a_result)
        # print(a_result)
        b_result=[]
        self.key_extraction(b,0,b_result)
        # print(b_result)
        sim = jellyfish.jaro_distance(str(a_result),str(b_result))
        # print(a_result)
        # print(b_result)
        return sim


    def parse_m4a(self, data_in):
        offset = 0
        output_dict ={}
        if self.ascii_check(data_in[offset+4:offset+8]) == 0:
            return -1
        while(offset < len(data_in)):
            length = int.from_bytes(data_in[offset:offset+4],byteorder='big')
            
            name = data_in[offset+4:offset+8].decode('utf-8')
            #if header length =1
            #large box
            if length == 1:
                length = int.from_bytes(data_in[offset+8:offset+16],byteorder='big')
                #if header length =8
                if self.ascii_check(data_in[offset+12:offset+16]) and int.from_bytes(data_in[offset+8:offset+12],byteorder='big') > 8 and int.from_bytes(data_in[offset+8:offset+12],byteorder='big') <= len(data_in[offset+8:offset+length]):
                    data= data_in[offset+8:offset+length]
                    output_dict[name] = [data,self.parse_m4a(data)]

                #if header length =12
                elif self.ascii_check(data_in[offset+16:offset+20]) and int.from_bytes(data_in[offset+12:offset+16],byteorder='big') > 8 and int.from_bytes(data_in[offset+8:offset+12],byteorder='big') <= len(data_in[offset+8:offset+length]):
                    data= data_in[offset+12:offset+length]
                    output_dict[name] = [data,self.parse_m4a(data)]
                else:
                    output_dict[name]=[data_in[offset+16:offset+length]]

            #if header length =8
            elif self.ascii_check(data_in[offset+12:offset+16]) and int.from_bytes(data_in[offset+8:offset+12],byteorder='big') > 8 and int.from_bytes(data_in[offset+8:offset+12],byteorder='big') <= len(data_in[offset+8:offset+length]):
                data= data_in[offset+8:offset+length]
                output_dict[name] = [data,self.parse_m4a(data)]
            
            
            #if header length =12
            elif self.ascii_check(data_in[offset+16:offset+20]) and int.from_bytes(data_in[offset+12:offset+16],byteorder='big') > 8 and int.from_bytes(data_in[offset+8:offset+12],byteorder='big') <= len(data_in[offset+8:offset+length]):
                data= data_in[offset+12:offset+length]
                output_dict[name] = [data,self.parse_m4a(data)]

            else:
                output_dict[name] = [data_in[offset+8:offset+length]]
            
            offset += length
        return output_dict
    def ios_multimedia_meta(self):
        try:
            output = self.output
            # esds = output['moov'][1]['trak'][1]['mdia'][1]['minf'][1]['stbl'][1]['stsd'][1]['mp4a'][1]['esds'][0]
            self.sample_rate= int.from_bytes(output['moov'][1]['trak'][1]['mdia'][1]['minf'][1]['stbl'][1]['stsd'][0][40:42], byteorder='big')
            self.buffer_size = int.from_bytes(output['moov'][1]['trak'][1]['mdia'][1]['minf'][1]['stbl'][1]['stsd'][0][72:74], byteorder='big')
            self.maximum_bit_rate=int.from_bytes(output['moov'][1]['trak'][1]['mdia'][1]['minf'][1]['stbl'][1]['stsd'][0][75:78], byteorder='big')
            self.average_bit_rate = int.from_bytes(output['moov'][1]['trak'][1]['mdia'][1]['minf'][1]['stbl'][1]['stsd'][0][79:82], byteorder='big')
            if self.buffer_size ==6144 and self.sample_rate==48000 and self.maximum_bit_rate==64000 and self.average_bit_rate==64000:
                self.iphone_normal_flag =1

            else :
                self.iphone_abnormal_flag=1
                self.log=self.log +"아이폰의 기본(default)와 다른 sample rate 또는 buffer size 또는 bit rate 값을 가지고 있습니다. "
        except:
            self.iphone_but_abnormal_flag = 1
            self.log=self.log+"아이폰 문자열이 발견되었지만 구조에 이상이 있습니다."
            self.sample_rate=-1
            self.buffer_size =-1 
            self.maximum_bit_rate = -1
            self.average_bit_rate =-1 
        return self.sample_rate, self.buffer_size, self.maximum_bit_rate, self.average_bit_rate 
            

    def multimedia_meta(self):
        try: 
                output = self.output
                self.sample_rate= int.from_bytes(output['moov'][1]['trak'][1]['mdia'][1]['minf'][1]['stbl'][1]['stsd'][0][40:42], byteorder='big')
                finds = output['moov'][1]['trak'][1]['mdia'][1]['minf'][1]['stbl'][1]['stsd'][0][::-1]
                tag_pos1 = finds.find(b'\x05')
                self.average_bit_rate = int.from_bytes(finds[tag_pos1+1:tag_pos1+4], byteorder='little')
                self.maximum_bit_rate =int.from_bytes(finds[tag_pos1+5:tag_pos1+8], byteorder='little')
                self.buffer_size =int.from_bytes(finds[tag_pos1+9:tag_pos1+12], byteorder='little')     
                # print(self.sample_rate, self.average_bit_rate, self.maximum_bit_rate,self.buffer_size )         

        except:
            # import traceback
            # print(traceback.print_exc())
            self.sample_rate=-1
            self.buffer_size =-1 
            self.maximum_bit_rate = -1
            self.average_bit_rate =-1 
        return self.sample_rate, self.buffer_size, self.maximum_bit_rate, self.average_bit_rate 

    def check_ios_str(self):
        try:
            output = self.output
            find_iphone = hex(int.from_bytes(output['moov'][1]['udta'][1]['meta'][1]['ilst'][0], byteorder='big'))   
            iphonestr='636f6d2e6170706c652e566f6963654d656d6f73'
            if iphonestr in find_iphone:
                self.iphone_flag=1

        except:
            return 0
        return 1

    def incorrect_meta(self):

        #check abnormal timestamp
        output = self.output
        try:
            self.encoding_create=int.from_bytes(output['moov'][1]['mvhd'][0][4:8], byteorder='big')
            self.encoding_mod=int.from_bytes(output['moov'][1]['mvhd'][0][8:12], byteorder='big')
            self.recording_create=int.from_bytes(output['moov'][1]['trak'][1]['tkhd'][0][4:8], byteorder='big')
            self.recording_mod=int.from_bytes(output['moov'][1]['trak'][1]['tkhd'][0][8:12], byteorder='big')
            if self.encoding_create:
                self.encoding_create_local = self.timeto_hfs(self.encoding_create)
            if self.encoding_mod:
                self.encoding_mod_local = self.timeto_hfs(self.encoding_mod)
            if self.recording_create:
                self.recording_create_local = self.timeto_hfs(self.recording_create)
            if self.recording_mod:
                self.recording_mod_local = self.timeto_hfs(self.encoding_mod)
            if (self.recording_create and self.recording_mod and self.encoding_create and self.encoding_mod)==0:
                self.log = self.log+"비정상적인 시간값입니다. \n시간값이 0입니다. "
                self.wrong_time_flag =1
            # print(self.encoding_create_local, self.encoding_mod_local, self.recording_create_local, self.recording_mod_local)


            if abs(self.encoding_create-self.recording_create)>60:
                self.log= self.log+"\nencoding creat date 또는 recoding create date가 비정상적입니다. "
                self.abnormal_time_flag =1

            if (self.encoding_mod-self.encoding_create>60):
                self.log =self.log+"\nencoding modification time이 encoding_create time 보다 뒤입니다."
                self.abnormal_time_flag =1

            if (self.recording_mod-self.recording_create>60):
                self.log =self.log+"\nrecording modification tim이 recording_create time 보다 뒤입니다."
                self.abnormal_time_flag =1

        except: 
            self.log = self.log+"\nmvhd 또는 tkhd container가 존재하지 않거나, 구조가 비정상적입니다."
            self.abnormal_structure_flag =1
            # import traceback
            # traceback.print_exc()
        
        #check mac, ios multimedia metadata
        self.iphone_flag = self.check_ios_str()
        
        if self.iphone_flag :
            sample_rate, buffer_size, maximum_bit_rate, average_bit_rate  = self.ios_multimedia_meta()

        else: #not ios/mac format 
            sample_rate, buffer_size, maximum_bit_rate, average_bit_rate  = self.multimedia_meta()
        if (sample_rate and buffer_size and maximum_bit_rate and average_bit_rate)==0:
            self.multimedia_meta_flag=1
        elif sample_rate== -1 or buffer_size==-1 or maximum_bit_rate==-1 or average_bit_rate==-1:
            self.multimedia_meta_error_flag=1

    def is_manipulated_1(self):
        if self.abnormal_time_flag: #시간값 차이 이상있을 경우
            self.manipulated_score=self.manipulated_score*0.6
            # print("시간값 차이 이상있을 경우")
        if self.structure_error_flag: #container 구조에 이상있을 경우
            self.manipulated_score=self.manipulated_score*0.5
            # print("container 구조에 이상있을 경우")
        if self.wrong_time_flag: #시간값이 0으로 초기화
            # print("시간값이 0으로 초기화")
            self.manipulated_score=self.manipulated_score*0
        if self.abnormal_structure_flag: #mvhd, tkhd 구조 이상
            # print("mvhd, tkhd 구조 이상")
            self.manipulated_score = self.manipulated_score*0.5
        if self.iphone_abnormal_flag: #ios, mac 기본 멀티미디어 메타데이터가 알려진 메타데이터와 상이한 경우
            # print("ios, mac 기본 멀티미디어 메타데이터가 알려진 메타데이터와 상이한 경우")
            self.manipulated_score = self.manipulated_score*0.65
        if self.iphone_but_abnormal_flag: #ios, mac 문자열을 확인했지만, 구조가  다른경우
            # print("ios, mac 문자열을 확인했지만, 구조가  다른경우")
            self.manipulated_score = self.manipulated_score*0.65
        if self.multimedia_meta_flag:#멀티미디어 메타데이터가 0인 경우 
            # print("멀티미디어 메타데이터가 0인 경우 ")
            self.manipulated_score = self.manipulated_score*0.6
        if self.multimedia_meta_error_flag:#멀티미디어 메타데이터 파싱과정에서의 구조 에러
            self.manipulated_score = self.manipulated_score*0.5
            # print("멀티미디어 메타데이터 파싱과정에서의 구조 에러")
        return self.manipulated_score

    # def check_same_meta(self):


def single_file_mode(data):
    parsing = m4a_parser(data)
    parsing.incorrect_meta()
    parsing.is_manipulated_1()
    strings = ""
    manipulated_flag=0
    if parsing.manipulated_score <70:
        manipulated_flag =1
        strings = strings+"파일 내부의 메타데이터가 비정상적이므로 변조 되었습니다. "
        # print(parsing.log)
    return parsing.manipulated_score, strings, manipulated_flag

def multi_file_mode(data1, data2):
    strings = ""
    manipulated_flag=0
    metadata_same_score =0
    parsing = m4a_parser(data1)
    parsing2 = m4a_parser(data2)
    if parsing.check_ios_str():
        sample_rate1, buffer_size1, maximum_bit_rate1, average_bit_rate1 = parsing.ios_multimedia_meta()
        sample_rate2, buffer_size2, maximum_bit_rate2, average_bit_rate2 = parsing2.ios_multimedia_meta()
    else:
        sample_rate1, buffer_size1, maximum_bit_rate1, average_bit_rate1 = parsing.multimedia_meta()
        sample_rate2, buffer_size2, maximum_bit_rate2, average_bit_rate2 = parsing2.multimedia_meta()

    
    parsing.incorrect_meta()
    parsing.is_manipulated_1()
    similarity = float(parsing.structure_comp(parsing.output,parsing2.output))*100
    # print(similarity)
    if (sample_rate1!=sample_rate2) or (maximum_bit_rate1!=maximum_bit_rate2) or (average_bit_rate1!=average_bit_rate2) or (buffer_size1 != buffer_size2):
        metadata_same_score=1
    if parsing.manipulated_score <70:
        manipulated_flag =1
        strings = strings+"파일 내부의 메타데이터가 비정상적입니다. "
    if similarity < 89:
        manipulated_flag =1
        strings = strings+"정상 파일의 구조와 비교한 결과, 구조 유사도가 낮습니다. "
    if metadata_same_score:
        manipulated_flag =1
        strings = strings+"정상 파일의 구조와 비교한 결과, 메타데이터 sample_rate1, buffer_size1, maximum_bit_rate1, average_bit_rate1 의 값이 다릅니다."
    
    return parsing.manipulated_score, strings, manipulated_flag, metadata_same_score, similarity

        


def usage():
    print("USAGE : python parser.py FILE [FILE]")
    print("ex) python parser.py [abnormal_file]")
    print("ex) python parser.py [normal file] [abnormal_file]")
    print("")

if __name__ == "__main__":

    if len(sys.argv) < 2:
        usage()

    elif len(sys.argv) == 2:
        #single file mode
        manipulated_score, strings, manipulated_flag = single_file_mode(open(sys.argv[1],'rb').read())
        if manipulated_flag:
            print(sys.argv[1], " 파일이 변조되었습니다.")
            print(strings)
        else: 
            print("변조되지 않았습니다")
        print("정상파일일 확률 : ", manipulated_score)
        #Validate Metadata

    elif len(sys.argv) == 3:
        #multiple file mode
        manipulated_score, strings, manipulated_flag, metadata_same_score, similarity = multi_file_mode(open(sys.argv[1],'rb').read(), open(sys.argv[2],'rb').read())
        if manipulated_flag:
            print(sys.argv[1], "파일이 변조되었습니다.")
            print(strings)
        else: 
            print("변조되지 않았습니다")


