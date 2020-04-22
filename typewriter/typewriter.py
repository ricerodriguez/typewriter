#!/usr/bin/env python
"""
Generates images and video from code with a typewriter effect (typing one character at a time)
"""
__author__ = 'Victoria (Rice) Rodriguez'
__package__ = "typewriter"

import os, sys
import cv2
import argparse
import logging
import numpy as np
from PIL import Image
from threading import Thread
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import (get_lexer_by_name,get_lexer_for_filename,guess_lexer)

class Typewriter:
    def __init__(self,**args):
        """
        Generates images and video from code with a typewriter effect (typing one character at a time). 
        """
        self.args = args
        self.lexer = get_lexer_for_filename(args['textfile']) if self.args['language'] is None else get_lexer_by_name(self.args['language'])

        logger.debug(f'Assigned value to lexer object {self.lexer}')
        self.formatter = self.__get_formatter()
        logger.debug(f'Assigned value to formatter object {self.formatter}')
        self._image_paths = []
        self._progress=0
        self._impath=''
        self.images = []
        self.total=0
        self.total_size=0
        try:
            with open(args['textfile'],'r') as f:
                self._content = f.read()
        except FileNotFoundError as err:
            logger.error(err)
            sys.exit(-1)

    def __get_formatter(self):
        return ImageFormatter(line_numbers=True,style=self.args['style'],line_number_bg=None,font_size=self.args['font_size'])

    def __get_lexer(self,content):
        lexer = guess_lexer(content) if self.args['language'] is None else get_lexer_by_name(self.args['language'])
        return lexer

    def __update_progress(self):
        '''
        Adapted into fewer lines from the following gist:
        https://gist.github.com/vladignatyev/06860ec2040cb497f0f3
        '''
        sys.stdout.write(f'[{"="*int(round(50*self.progress/float(self.total)))+"-"*(50-int(round(50*self.progress/float(self.total))))} {round(100.0*self.progress/float(self.total),1)}%]\r')
        sys.stdout.flush()

    def __make_dir(self):
        choice=''
        if not os.path.exists('tmp'):
            os.makedirs('tmp')
        else:
            while not choice == 'y':
                logger.warning('There is already a directory named "tmp" here. Please make sure you are okay with everything in this "tmp" folder getting deleted before continuing.')
                choice=input('Continue? y/n\n')
                if choice == 'y':
                    break
                elif choice == 'n':
                    sys.exit(-1)
                else:
                    logger.warning('Invalid choice. Please type "y" or "n".\n')
                    continue

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self,val):
        self._content=val
        self.__get_lexer(self._content)
        self.__get_formatter()

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self,val):
        self._progress=val
        self.__update_progress()

    @property
    def impath(self):
        return self._impath

    @impath.setter
    def impath(self,val):
        self._impath=val
        self._image_paths.append(self._impath)
        old = Image.open(self._impath)
        new=Image.new('RGBA',self.total_size)
        new.paste(old)
        new.save(self._impath)
        self.images.append(new)

    @property
    def image_paths(self):
        return self._image_paths

    @image_paths.setter
    def image_paths(self,val):
        self._image_paths=val
        self.images=[Image.open(f) for f in self._image_paths]
        
    def generate_images(self,content=None):
        '''
        Generate Images
        ---------------
        Description: Creates a list of image data given text content
        '''
        if content is None:
            content=self.content
        else:
            self.content = content

        self.__make_dir()
        self.total=len(content)
        code = ''
        logger.info('Generating images...')
        blank='\n'.join([' '*len(line) for line in content.splitlines()])
        last_impath=os.path.join('tmp',f'tmp_{str(len(content)).zfill(5)}.png')
        highlight(blank,self.lexer,self.formatter,outfile=last_impath)

        im=Image.open(last_impath).convert('RGBA')
        self.total_size=im.size
        self.images.append(im)
        os.remove(last_impath)
        for line in content:
            for ch in line:
                self.progress+=1
                impath=os.path.join('tmp',f'tmp_{str(self.progress).zfill(5)}.png')
                highlight(code,self.lexer,self.formatter,outfile=impath)
                self.impath=impath
                code += ch

        print()
        return self.image_paths

    def generate_movie(self,image_paths=None,**args):
        '''
        Generate Movie
        --------------
        Description: Creates an animation of the images generated above,
                     and then cleans up the tmp files by removing everything
                     in the tmp directory that was generated.
        '''
        # If it's run without a list of images and we haven't generated any images yet,
        # then generate the images and set the var to that
        logger.info('Generating movie...')
        if image_paths is None and not self.image_paths:
            image_paths=self.generate_images(self.content)
        # If we have already generated the images then set the var to that
        elif image_paths is None:
            image_paths=self.image_paths
        # If they gave us the list of images, put out something to make sure
        # user knows to keep the content matching
        else:
            logger.info('Make sure the content of the images matches the content var in this class!')

        frame=cv2.imread(self.image_paths[0])
        h,w,l=frame.shape
        v=cv2.VideoWriter('movie.avi' if 'out' not in args else args['out'],0,10 if 'fps' not in args else args['fps'],(w,h))
        self.progress=0
        self.total=len(self.image_paths)+1
        for im in self.image_paths:
            v.write(cv2.imread(im))
            os.remove(im)
            self.progress += 1

        os.rmdir('tmp')
        self.progress+=1
        print()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Creates a video of typing text given a text file')
    parser.add_argument('-v','--verbose',help='outputs logging to console',nargs='?',default='INFO',metavar='LOG LEVEL',choices=['DEBUG','debug','INFO','info','WARNING','warning','ERROR','error','CRITICAL','critical'])
    parser.add_argument('-l','--language',help='manually choose language of textfile, leave blank to auto-detect')
    parser.add_argument('-s','--style',help='choose pygments style for syntax highlighting, defaults to monokai',default='monokai')
    parser.add_argument('--font_size',help='size of font, defaults to 14',default=14)
    parser.add_argument('--fps',help='fps of output video, defaults to 10',default=10)
    parser.add_argument('-o','--out',help='name of output file, defaults to movie.avi',default='movie.avi')
    parser.add_argument('textfile',help='text file of the text that should be typed in the video')
    args = vars(parser.parse_args())

    logger = logging.getLogger('Typewriter')
    log_cmd = logging.StreamHandler()
    logger.addHandler(log_cmd)

    try:
        if args['verbose'].lower() == 'debug':
            logger.setLevel(logging.DEBUG)
        elif args['verbose'].lower() == 'info':
            logger.setLevel(logging.INFO)
        elif args['verbose'].lower() == 'warning':
            logger.setLevel(logging.WARNING)
        elif args['verbose'].lower() == 'error':
            logger.setLevel(logging.ERROR)
        elif args['verbose'].lower() == 'critical':
            logger.setLevel(logging.CRITICAL)
        else:
            logger.setLevel(logging.WARNING)
    except KeyError:
        logger.setLevel(logging.WARNING)

    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    log_cmd.setFormatter(formatter)
    logger.debug('Set log level for console.')


    tw = Typewriter(**args)
    steps = 0
    content = ''
    with open(args['textfile'],'r') as f:
        content = f.read()
        steps = len(content)

    tw.generate_images(content)
    tw.generate_movie(**args)

