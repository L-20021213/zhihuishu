import time
import base64
from rich.console import Console
import src.encode.ev as ev
import threading


console = Console()

watchpoint = ''
done = 0
exam_done = 0
cache_time = 0
data_time = 0


def get_status(s,lessonid,recruit,uuid,tp):
    # console.log("获取视频课程完成进度:")
    url = 'https://studyservice.zhihuishu.com/learning/queryStuyInfo'
    data = {
        'recruitId': recruit,
        'uuid': uuid,
        'dateFormate': str(int(time.time())) + str('000'),
    }
    if tp == 'big':
        data["lessonIds[0]"] = lessonid
    else:
        data["lessonVideoIds[0]"] = lessonid
    resp = s.post(url,data=data)
    state = resp.json()['data']['lesson'][lessonid]['watchState']
    # console.log(state)
    return state


def get_token(s,courseid,chapterid,lessonid,recruit,videoid,uuid):
    # console.log("获取Token:")
    url = 'https://studyservice.zhihuishu.com/learning/prelearningNote'
    data = {
        'ccCourseId': courseid,
        'chapterId': chapterid,
        'isApply': 1,
        'lessonId': lessonid,
        'recruitId': recruit,
        'videoId': videoid,
        'uuid': uuid,
        'dateFormate': str(int(time.time())) + str('000')
    }
    resp = s.post(url,data=data)
    token = resp.json()['data']['studiedLessonDto']['id']
    token = base64.b64encode(str(token).encode('utf8')).decode('utf8')
    already = resp.json()['data']['studiedLessonDto']['learnTimeSec']
    # console.log(token)
    return token, already


def get_lastview(s,recruit,uuid):
    # console.log("获取最后一次观看的视频id：")
    url = 'https://studyservice.zhihuishu.com/learning/queryUserRecruitIdLastVideoId'
    data = {
        'recruitId': recruit,
        'uuid': uuid,
        'dateFormate': str(int(time.time())) + str('000'),
    }
    resp = s.post(url,data=data)
    # console.log(resp.json()['data']['lastViewVideoId'])
    return resp.json()['data']['lastViewVideoId']


def quiz_pointer(s,lessonid,recruit,courseid,uuid):
    """
    返回一个列表，里面是问题的详细信息[{"timeSec":49,"questionIds":"16162964"}]
    :param s:
    :param lessonid:
    :param recruit:
    :param courseid:
    :param uuid:
    :return:
    """
    url = 'https://studyservice.zhihuishu.com/popupAnswer/loadVideoPointerInfo'
    data = {
        'lessonId': lessonid,
        'recruitId': recruit,
        'courseId': courseid,
        'uuid': uuid,
        'dateFormate': str(int(time.time())) + str('000'),
    }
    resp = s.post(url,data=data)
    return resp.json()['data']['questionPoint']

def get_watchpoint():
    global watchpoint
    global done
    # console.log("获取watchpoint")
    if watchpoint == '':
        watchpoint = "0,1,"
    elif watchpoint != '0,1,':
        watchpoint += ("," + str(int(int(done) / 5) + 2))
    else:
        watchpoint += (str(int(int(done) / 5) + 2))
    # console.log(watchpoint)


def done2time(done):
    h = done // 3600
    m = (done - h * 3600) // 60
    s = done - h * 3600 - m * 60
    return "{}:{}:{}".format(str(h).rjust(2,'0'),str(m).rjust(2,'0'),str(s).rjust(2,'0'))


def save_database(s,ev,token,courseid,uuid,):
    global watchpoint
    global data_time
    # console.log("正在savedatabase")
    url = 'https://studyservice.zhihuishu.com/learning/saveDatabaseIntervalTime'
    data = {
        'watchPoint': watchpoint,
        'ev': ev,
        'learningTokenId': token,
        'courseId': courseid,
        'uuid': uuid,
        'dateFormate': str(int(time.time())) + str('000'),
    }
    resp = s.post(url,data=data)
    if resp.json()['data']['submitSuccess'] == True:
        console.log("[yellow]savedatabase[/yellow]成功")
        data_time += 1
    watchpoint = '0,1,'

def save_cache(s, ev, token, uuid):
    global watchpoint
    global cache_time
    # console.log("正在savecache")
    url = 'https://studyservice.zhihuishu.com/learning/saveCacheIntervalTime'
    data = {
        'watchPoint': watchpoint,
        'ev': ev,
        'learningTokenId': token,
        'uuid': uuid,
        'dateFormate': str(int(time.time())) + str('000'),
    }
    resp = s.post(url, data=data)
    console.log('[yellow]savecache[/yellow]成功')
    cache_time += 1
    watchpoint = '0,1,'


def do_exam(s, courseid, recruit, questionid, biglessonid, smalllessonid, answer,uuid):
    global exam_done
    # console.log("正在做题")
    url = 'https://studyservice.zhihuishu.com/popupAnswer/saveLessonPopupExamSaveAnswer'
    data = {
        'courseId': courseid,
        'recruitId': recruit,
        'testQuestionId': questionid,
        'isCurrent': 1,
        'lessonId': biglessonid,
        'lessonVideoId': smalllessonid,
        'answer': answer,
        'testType': 0,
        'uuid': uuid,
        'dateFormate': str(int(time.time())) + str('000'),
    }
    resp = s.post(url,data=data)
    if resp.json()['data']['submitStatus'] == True:
        console.log("题目[yellow]提交成功[/yellow]")
        exam_done += 1


def get_exam(s,biglessonid,smalllessonid,questionid,uuid):
    # console.log("正在获取题目")
    url = 'https://studyservice.zhihuishu.com/popupAnswer/lessonPopupExam'
    data = {
        'lessonId': biglessonid,
        'lessonVideoId': smalllessonid,
        'questionIds': questionid,
        'uuid': uuid,
        'dateFormate': str(int(time.time())) + str('000'),
    }
    resp = s.post(url,data=data)
    options = resp.json()['data']['lessonTestQuestionUseInterfaceDtos'][0]['testQuestion']['questionOptions']
    for option in options:
        if option['result'] == '1':
            # console.log("答案id为:{}".format(option['id']))
            return option['id']

def start_watch(s,courseid,chapterid,lessonid,recruit,videoid,uuid,video,totalwork,finished):
    console.log("开始视频任务id:{}".format(videoid))
    """
    每两秒watchpoint一次
    每五秒更新done一次
    每三分钟更新一次cache
    每五分钟更新一次database
    """
    global watchpoint
    global done
    global exam_done
    global cache_time
    global data_time

    tp = video['type']
    if video['type'] == 'big':
        smalllessonid = 0
        biglessonid = int(lessonid)
    else:
        smalllessonid = int(lessonid)
        biglessonid = int(video['lessonid'])

    quiz = quiz_pointer(s,lessonid,recruit,courseid,uuid)
    quiz = sorted(quiz,key = lambda q : q['timeSec'])

    watchpoint = ''
    done = 0
    exam_done = 0
    cache_time = 0
    data_time = 0

    # 初始化 全部更新一次
    token, done = get_token(s, courseid, chapterid, lessonid, recruit, videoid, uuid)
    lastview = get_lastview(s, recruit, uuid)
    get_watchpoint()
    save_database(s, ev.get_ev(
        [recruit, biglessonid, smalllessonid, lastview, chapterid, '0', done, video['videoSec'],
         done2time(video['videoSec'])]), token, courseid, uuid)

    global th_wa
    global th_do
    global th_ca
    global th_da
    global th_st
    global th_ex
    global th_ss
    th_wa = ThreadWithSwitch(get_watchpoint,(),2,name="Update WatchPoint")
    th_do = ThreadWithSwitch(thread_done,(),5,name="Update DoneTime")
    th_ca = ThreadWithSwitch(thread_cache,(s,recruit,chapterid,courseid,biglessonid,smalllessonid,uuid,videoid,video,tp),180,name="Save CacheData")
    th_da = ThreadWithSwitch(thread_data,(s,recruit,chapterid,courseid,biglessonid,smalllessonid,uuid,videoid,video,tp), 300,name="Save DataBase")
    th_st = ThreadWithSwitch(thread_status,(s,lessonid,recruit,uuid,tp),10,name="Watch Status")
    th_ex = ThreadExam(s, quiz,biglessonid,smalllessonid,uuid,courseid,recruit,name="Exam Check")
    th_ss = ThreadWithSwitch(show_status,(lessonid,video['videoSec'],len(quiz),totalwork,finished),5,name="Show Status")

    th_wa.start()
    th_do.start()
    th_ca.start()
    th_da.start()
    th_ex.start()
    th_ss.start()
    th_st.start()

    th_st.join()

def show_status(lessonid,totaltime,totalexam,totalwork,finished):
    global done
    global exam_done
    global data_time
    global cache_time
    status = ('#' * int(float(done) / float(totaltime) * float(20))).ljust(20,'-')
    console.print("任务ID：[yellow]{}[/yellow]  进度 {} [red]{}[/red]秒/[red]{}[/red]秒  测验：[red]{}[/red]/[red]{}[/red]  Cache:[red]{}[/red]次  Data:[red]{}[/red]次 总任务:[red]{}[/red]/[red]{}[/red]".format(lessonid,status,done,totaltime,exam_done,totalexam,cache_time,data_time,finished,totalwork),end='\r')


class ThreadExam(threading.Thread):
    def __init__(self,s, quiz,biglessonid,smalllessonid,uuid,courseid,recruit,name='',isrun=True):
        self.isrun = isrun
        self.s = s
        self.quiz = quiz
        self.biglessonid = biglessonid
        self.smalllessonid = smalllessonid
        self.uuid = uuid
        self.courseid = courseid
        self.recruit = recruit
        super().__init__(name = name)

    # 重写父类的run方法
    def run(self):
        global done
        for q in self.quiz:
            while True:
                if done >= q['timeSec']:
                    keyid = get_exam(self.s, self.biglessonid, self.smalllessonid, q['questionIds'], self.uuid)
                    do_exam(self.s, self.courseid, self.recruit, q['questionIds'], self.biglessonid, self.smalllessonid, keyid, self.uuid)
                    break
                # console.log('未到做题时间')
                time.sleep(10)


class ThreadWithSwitch(threading.Thread):
    def __init__(self,func,args,wait,name='',isrun=True):
        self.isrun = isrun
        self.wait = wait
        super().__init__(target = func,args = args,name = name)

    # 重写父类的run方法
    def run(self):
        global watchpoint
        global done
        while self.isrun:
            time.sleep(self.wait)
            self._target(*self._args)



# def thread_study(s,recruit,schoolid,uuid):
#     url = 'https://studyservice.zhihuishu.com/course/queryStudiedTimeLimitInfo?recruitId='+str(recruit)+'&schoolId='+str(schoolid)+'&uuid='+str(uuid)+'&dateFormate='+str(int(time.time())) + str('000')
#     resp = s.get(url)
#     isavailable = resp.json()['data']['canBeStudyNow']



def thread_done():
    global done
    done += 5


def thread_cache(s,recruit,chapterid,courseid,biglessonid,smalllessonid,uuid,videoid,video,tp):
    global watchpoint
    global done
    if tp == 'big':
        lessonid = biglessonid
    else:
        lessonid = smalllessonid
    token = get_token(s, courseid, chapterid, lessonid, recruit, videoid, uuid)
    lastview = get_lastview(s, recruit, uuid)
    save_cache(s, ev.get_ev(
        [recruit, chapterid, courseid, biglessonid, done2time(done), done, lastview, smalllessonid, done]), token, uuid)


def thread_data(s,recruit,chapterid,courseid,biglessonid,smalllessonid,uuid,videoid,video,tp):
    global watchpoint
    global done
    if tp == 'big':
        lessonid = biglessonid
    else:
        lessonid = smalllessonid
    token = get_token(s, courseid, chapterid, lessonid, recruit, videoid, uuid)
    lastview = get_lastview(s, recruit, uuid)
    save_database(s, ev.get_ev(
        [recruit, biglessonid, smalllessonid, lastview, chapterid, '0', done, video['videoSec'],
         done2time(video['videoSec'])]), token, courseid, uuid)


def thread_status(s,lessonid,recruit,uuid,tp):
    status = get_status(s,lessonid,recruit,uuid,tp)
    if status == 1:
        th_wa.isrun = False
        th_do.isrun = False
        th_ca.isrun = False
        th_da.isrun = False
        th_st.isrun = False
        th_ex.isrun = False
        th_ss.isrun = False

def watch_all(s,all_videos,lessons,courseid,recruit,uuid, finished):
    for lesson in lessons:
        for video in all_videos:
            if int(video['id']) == int(lesson):
                start_watch(s,courseid,video['chapterid'],lesson,recruit,video['videoId'],uuid,video,len(all_videos), finished)
                finished += 1
                console.log("当前视频任务{}已完成，5秒后启动下一个视频任务".format(video['videoId']))
                time.sleep(5)

# 4248454d4d51554a4a404443585343494b4f4659554b4c494f455a544a4a4541475356414a4b444f5c574c4140444e5a54404a40
# 4248454d4d51554a4a404443585343494b444f58574b4b464d4f5b544a4a404141595d4841404f4151554f4140444e5a54404842
