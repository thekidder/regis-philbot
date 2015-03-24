#!/usr/bin/env python

# ************************** #
#     Regis Philbot v1.0     #
#      Slack Trivia Bot      #
#                            #
#             by             #
#      Patrick Hennessy      #
#                            #
#      github.com/ph7vc      #
# ************************** #

import sys
import time
import math
import re
import random
import urlparse
import requests
import traceback
import BaseHTTPServer
import json

_PORT = 1337
_SAVE_FILENAME = 'save.json'

expectedRequestKeys = ['user_id','channel_name','timestamp','team_id','channel_id','token','text','service_id','team_domain','user_name']

def main():
  bot = Trivia()
  try:
    bot.run()
  except KeyboardInterrupt:
    prettyPrint("Caught keyboard interrupt")
  except Exception as e:
    prettyPrint("Caught exception: {}".format(e))
    prettyPrint(traceback.format_exc())
  finally:
    prettyPrint("Shutting down")
    bot.save()
    sys.exit(1)

class Trivia():
  askedQuestions = {}
  currentQuestion = 0
  questionSet = ''
  timer = time.time()
  hintGiven = False
  quietCount = 0
  
  def __init__(self):
    self.httpd = BaseHTTPServer.HTTPServer(('', _PORT), RequestHandler)
    self.httpd.socket.settimeout(1)
    self.httpd.message_queue = []


    random.seed()

    prettyPrint("Starting Regis Philbot")
  
    self.loadConfig()
    self.loadQuestions()
    self.load()
    self.answerFound = False

    if self.config["questions"] not in self.askedQuestions:
      self.askedQuestions[self.config["questions"]] = {}

    if self.questionSet not in self.askedQuestions[self.config["questions"]]:
      self.askedQuestions[self.config["questions"]][self.questionSet] = set()

    self.currentQuestion = random.randint(0, len(self.questions[self.questionSet]) - 1)
    self.getNextQuestion()

  def loadConfig(self):
    prettyPrint("Loading config...")

    with open('conf/bot.json', 'r') as configFile:
      self.config = json.loads(configFile.read())

  # Load the questions from a file storing into dict
  def loadQuestions(self):
    prettyPrint("Loading questions from: \"" + self.config["questions"] + "\"")
    
    with open("questions/{}".format(self.config["questions"]), "r") as file:
      self.questions = json.load(file, encoding='utf-8')
    self.questionSet = self.config["questionSet"]

  def load(self):
    try:
      with open(_SAVE_FILENAME, 'r') as f:
        data = json.loads(f.read())
        if 'scores' in data:
          self.money = data['scores']
        if 'asked' in data:
          self.askedQuestions = data['asked']
          for key,val in self.askedQuestions.iteritems():
            for questionSet,questions in val.iteritems():
              self.askedQuestions[key][questionSet] = set(val)
      prettyPrint('loaded scores')
    except IOError:
      prettyPrint('no scores to load')
      self.money = {}

  def save(self):
    # transform sets back to lists
    savedQuestions = {}
    for key,val in self.askedQuestions.iteritems():
      savedQuestions[key] = {}
      for questionSet,questions in val.iteritems():
        savedQuestions[key][questionSet] = list(questions)
    save = {
      'scores': self.money,
      'asked': savedQuestions,
    }
    save_data = json.dumps(save)
    with open(_SAVE_FILENAME, 'w') as f:
      f.write(save_data)
  
  def startTimer(self):
      self.timer = time.time()

  def getElapsedTime(self):
      return time.time() - self.timer 

  def delay(self, seconds):
    self.startTimer()
    while self.getElapsedTime() < seconds:
      self.httpd.handle_request()
  
  def askQuestion(self):
    self.answerFound = False
    self.hintGiven = False
    
    self.askedQuestions[self.config['questions']][self.questionSet].add(self.currentQuestion)
    question = self.questions[self.questionSet][self.currentQuestion]["question"]
    answer = self.questions[self.questionSet][self.currentQuestion]["answer"]

    if not(question == None):
      prettyPrint("[" + self.config["questions"][:-5].capitalize() + "." + self.questionSet.capitalize() + " " + hex(self.currentQuestion) + "] " + color.reset + question + " [" + answer + "]")
      sendMessage(self.config['incomingHookURL'], self.config['botname'], self.config['channel'], "[" + self.config["questions"][:-5].capitalize() + "." + self.questionSet.capitalize() + " " + hex(self.currentQuestion) + "] " + question)
    
  def listenForAnswers(self):
    self.httpd.handle_request()
    while len(self.httpd.message_queue):
      post = self.httpd.message_queue[0]
      self.httpd.message_queue = self.httpd.message_queue[1:]

      if post["token"][0] != self.config['outgoingToken']:
        continue

      if float(post["timestamp"][0]) < float(self.timer):
        return

      if self.checkAnswer(post['text']):
        self.answerFound = True
        self.givePoints(post['user_id'][0], post['user_name'][0])
    
  def checkAnswer(self, msg):
    answer = self.questions[self.questionSet][self.currentQuestion]["answer"]
    regexp = self.questions[self.questionSet][self.currentQuestion]["regexp"]
    first_hash = answer.find('#')
    last_hash = answer.rfind('#')

    if first_hash != -1 and last_hash != -1 and first_hash != last_hash:
      answer = answer[first_hash+1:last_hash]
    
    if msg.lower().find(answer.lower()) != -1 or (regexp and re.search(regexp, msg.lower(), flags=re.IGNORECASE) is not None):
      return True
    else:
      return False

  def getNextQuestion(self):
    while self.currentQuestion in self.askedQuestions[self.config["questions"]][self.questionSet]:
      self.currentQuestion = random.randint(0, len(self.questions[self.questionSet]) - 1)

  def givePoints(self, userid, username):
    self.getNextQuestion()

    if userid not in self.money:
      self.money[userid] = 0
    self.money[userid] += 10
    prettyPrint("Correct answer given by: " + username, 1)  
    sendMessage(self.config['incomingHookURL'], self.config['botname'], self.config['channel'], "Correct! " + username + ", you earned $10!")
    sendMessage(self.config['incomingHookURL'], self.config['botname'], self.config['channel'], "Your riches have amassed to a staggering ${}!".format(self.money[userid]))
  
  def giveAnswer(self):
    answer = self.questions[self.questionSet][self.currentQuestion]["answer"]
      
    self.quietCount += 1    
      
    if not(answer == None):   
      prettyPrint("Answer was: " + answer, 1)
      sendMessage(self.config['incomingHookURL'], self.config['botname'], self.config['channel'], "Times up! The answer was: " + answer.replace('#', ''))
  
    self.getNextQuestion()    
  
  def giveHint(self):
    if(self.hintGiven):
      return
    else:
      self.hintGiven = True   
    
    random.seed()
    answer = self.questions[self.questionSet][self.currentQuestion]["answer"]
    hint = list("_" * len(answer))
    
    nReveal = int(math.ceil(float(len(answer)) * 0.25))

    for i in range(0, nReveal):
      rand = random.randint(0, nReveal)     
      hint[rand] = answer[rand] 

    finalHint = str("".join(hint))
    
    prettyPrint("Giving hint: " + finalHint,1)
    sendMessage(self.config['incomingHookURL'], self.config['botname'], self.config['channel'], "Heres a hint: " + finalHint) 

  def run(self):
    sendMessage(self.config['incomingHookURL'], self.config['botname'], self.config['channel'], self.config["botname"] + " initalizing...")
    self.delay(random.randint(1, 5))
    
    while True:
      if self.quietCount >= 25:
        prettyPrint("Stopping due to inactivity. Will resume on request")
        sendMessage(self.config['incomingHookURL'], self.config['botname'], self.config['channel'], "Stopping trivia due to inactivity. Will resume on request")  
        break 
      
      self.startTimer()   
      self.askQuestion()
      
      while self.getElapsedTime() < 40:
        self.listenForAnswers()
        
        if (self.answerFound):
          break

        if(int(self.getElapsedTime()) == 20):
          self.giveHint()
          
      if not(self.answerFound):
        self.giveAnswer()

      self.delay(random.randint(15,30))
    
      
class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  def log_message(self, format, *args):
    return

  def do_GET( self ):
    self.send_response(418)
    self.end_headers()
    
  def do_POST( self ):
    self.send_response(200)
    self.end_headers()
    
    request_len = int(self.headers['Content-Length'])
    request = self.rfile.read(request_len)

    post = urlparse.parse_qs(request)
    
    if not(set(expectedRequestKeys).issubset(post.keys())):
      return
    
    elif ( post["user_name"][0] == 'slackbot' ):
      return

    self.server.message_queue.append(post)
    
# Aux functions for output stuff
class color():
  reset  = '\033[0m'
  gray = '\033[1;30m' 
  red  = '\033[1;31m'   
  green  = '\033[1;32m'   
  yellow  = '\033[1;33m'  
  white = '\033[1;37m'  
    
def prettyPrint(msg, tabLevel=0):
  timestamp = time.strftime("%H:%M:%S")
  date = str(time.strftime("%x")).replace("/", "-")

  print "\t" + color.white + "[" + color.yellow + "Regis Philbot v1.0" + color.white + "] " + color.gray + timestamp + " " + color.reset + ("\t" * tabLevel) + msg

  file = open("logs/" + date + ".log", "a+")
  file.write( "[Regis Philbot v1.0] " + timestamp + " " + ("\t" * tabLevel) + msg + "\n") 
  file.close()

def sendMessage(url, name, channel, msg):
  msg = msg.replace('"', '\\"')
  data = '{"channel": "' + channel + '", "username": "' + name + '", "text":"' + msg + '"}'
  response = requests.post(url, data=data)

  if not(str(response) == "<Response [200]>"):
    prettyPrint(color.red + "ERROR: " + color.reset + "Send message failed.")
      
# Startup function  
if __name__ == '__main__':
  main()