#!/usr/bin/env python3

# -*- coding: utf-8 -*-
# vim: et ts=2

import os,argparse,re
DIAGEN_FILES = [
    "B-Zone",
    "Incubator",
    "Lampasso",
    "Ogorod",
    "Podish",
    "Spobs",
    "Threall",
    "VigBoo",
    "ZeePa",
    "Inventory"
]
QUERY_TITLE_RE = re.compile(r"\[(.+)\]\s+\[(.+)\]")

parser = argparse.ArgumentParser()
parser.add_argument('-D', '--output-dir', default='./po', help='where to put generated files')
parser.add_argument('-F', '--only-file', help='Only process specific file, useful for debugging. Possible values: {}'.format(DIAGEN_FILES))
parser.add_argument('-t', '--skip-text', action='store_true',default=False, help='Skip parsing .text files, useful for debugging')
parser.add_argument('-q', '--skip-query', action='store_true',default=False, help='Skip parsing .query files, useful for debugging')
parser.add_argument('diagen_dir', nargs=1, help='diagen directory with game texts')
args = parser.parse_args()

def is_ascii(s):
    # Credits: @stalkerg :)
    return all(ord(c) < 128 for c in s)

def get_files_to_convert(base_path):
  """
  Reads directory specified by `base_path` and generates a list of files to
  work on further based on command line flags.
  
  Returns: list of filenames to process further.
  """
  files_to_convert = []
  base_path_files = os.listdir(base_path)
  if not args.only_file:
    filenames_to_process = DIAGEN_FILES
  else:
    filenames_to_process = [args.only_file]
  for _file in filenames_to_process:
    text_file = "{}.text".format(_file)
    query_file = "{}.query".format(_file)
    if not text_file in base_path_files:
      print("!!! {} not found!".format(text_file))
    else:
      if not args.skip_text: files_to_convert.append(text_file)
    if _file == 'Inventory':
      continue # Inventory only have .text variant
    if not query_file in base_path_files:
      print("!!! {} not found!".format(query_file))
    else:
      if not args.skip_query: files_to_convert.append(query_file)

  return files_to_convert

def parse_diagen(source_file):
  """
  Parses single diagen file specified in `source_file` (.text or .query) and
  returns two dictionaries with Russian and English text; dictionary keys are
  section names (text between `[]` in the diagen files), values are just lists of
  strings of correcponding language with leading/ending spaces, and newlines
  stripped out (so an empty line will contain 0 characters in a list).
  No checks for file precence is made - caller should make sure the file exists and is readable.

  Returns: dict1, dict2
  """
  print(">>> Processing {}".format(source_file))
  lines_ru = {}
  lines_en = {}
  current_section = None
  
  with open(source_file, 'rb') as fh:
    is_rus_newline = True # Flag indicating the belonging of an empty line to RUS/ENG text
    for bytes_line in fh:
        str_line = bytes_line.decode('cp1251').strip().replace('"', '\\"') # NOTE: This strips '\n' too!
        if str_line.startswith('['): # New section started, get the title
          if QUERY_TITLE_RE.search(str_line): # .query has, ahem, weakly formalized section names...
            current_section = re.sub(QUERY_TITLE_RE,r'\1_\2',str_line)
          else:
            current_section = str_line.strip('[]')
          lines_en[current_section] = []
          lines_ru[current_section] = []
        else:
            # Within section - store strings in their respective arrays;
            # strings containing just '\n' were stripped down to 0 characters
            # already (see NOTE above)
            if not current_section: continue # Skip garbage at the beginning of the file
            if is_ascii(str_line) and len(str_line) > 0: # Looks like English text, and non-empty line
                lines_en[current_section].append(str_line)
                is_rus_newline = False # Unset the flag - if next line only contains '\n' we'll consider it as part of English text
            elif len(str_line) == 0: # Put empty line to the correct array based on `is_rus_newline`
                if is_rus_newline:
                    lines_ru[current_section].append(str_line)
                else:
                    lines_en[current_section].append(str_line)
            else: # Kakie washi dokazatelstva?..
                lines_ru[current_section].append(str_line)
                is_rus_newline = True # Indicate that if next line only contains '\n' - it's part of Russian text
  for section in lines_ru.keys():
    try:
      if len(lines_ru[section][-1]) == 0:
        lines_ru[section].pop()
    except IndexError:
      print("!!! Weird section name: {}".format(section))
  for section in lines_en.keys():
    try:
      if len(lines_en[section][-1]) == 0:
        lines_en[section].pop()
    except IndexError:
      print("!!! Weird section name: {}".format(section))

  return lines_ru, lines_en

def create_po(output_dir, component, text_ru, text_en):
  po_dir = "{}/{}".format(output_dir, component)
  po_file = "{}/en_US.po".format(po_dir)
  if not _mkdir(po_dir):
    print("!!! Will print the PO file to stdout")
    po_file = None
    pot_file = None
  po_str = ''
  pot_str = ''
  for msgctxt in text_ru.keys():
    po_str += 'msgctxt \"{}\"\n'.format(msgctxt)
    po_str += 'msgid \"\"\n'
    for line in text_ru[msgctxt]:
      if len(line) == 0:
        po_str += '\"\\n\"\n'
      else:
        po_str += "\"{}\\n\"\n".format(line)
    po_str += "msgstr \"\"\n"
    for line in text_en[msgctxt]:
      if len(line) == 0:
        po_str += '\"\\n\"\n'
      else:
        po_str += "\"{}\\n\"\n".format(line)
    po_str += '\n'
  with open(po_file, 'w') as fh:
    fh.write(po_str)
      
def _mkdir(folder):
  try:
    os.mkdir(folder)
  except FileExistsError:
    print("--- Output dir {} exists, continuing".format(folder))
  except PermissionError:
    print("!!! Permission denied when trying to create {}.".format(folder))
    return False
  return True


def main():
  for _file in get_files_to_convert(args.diagen_dir[0]):
    text_ru, text_en = parse_diagen("{}/{}".format(args.diagen_dir[0], _file))
    create_po(args.output_dir, _file, text_ru, text_en)

if __name__ == '__main__':
  if not _mkdir(args.output_dir):
    print("!!! Exiting.")
    raise SystemExit(1)
  if not os.path.isdir(args.diagen_dir[0]):
    print("!!! Diagen dir {} not found or not accessible!".format(args.diagen_dir[0]))
    raise SystemExit(1)
  main()
