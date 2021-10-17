import src.user.login as login
import src.course.show as show
import src.video.load as load
import src.video.watch as watch


import requests
import time



from rich.console import Console


console = Console()


if __name__ == '__main__':
    s = requests.session()
    usernm, info, uuid, schoolid, schoolnm, sharecourses = login.login_main(s)
    match = show.show_course(s,sharecourses,usernm)
    all_videos, lessons, finished = load.load_all(s,match['secret'],uuid,match['recruitid'],usernm)
    watch.watch_all(s, all_videos, lessons,match['courseid'],match['recruitid'],uuid, finished)
