#!/usr/bin/env python

import json
import sys

def main():
  input_filename = sys.argv[1]
  output_filename = sys.argv[2]

  output = {'trivia': []}

  with open(input_filename, 'r') as input_file:
    question = None
    category = None
    answer = None
    regexp = None
    for line in input_file:
      if line[0] == '#':
        continue
      parsed = line.split(': ')
      if len(parsed) < 2:
        continue
      var = parsed[0].strip()
      val = ': '.join(parsed[1:]).strip().decode('utf8', 'ignore')
      if var == 'Category':
        category = val
      elif var == 'Question':
        question = val
      elif var == 'Answer':
        answer = val
      elif var == 'Regexp':
        regexp = val
      if question and answer and category:
        output['trivia'].append({
          'question': question,
          'answer': answer,
          'category': category,
          'regexp': regexp
        })
        question = None
        answer = None
        category = None
        regexp = None
  with open(output_filename, 'w') as output_file:
    output_file.write(json.dumps(output, ensure_ascii=False, encoding='utf8', indent=2, separators=(',', ': ')))

if __name__ == '__main__':
  main()