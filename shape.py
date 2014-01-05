from OpenGL.GL import *
from OpenGL.GLU import *

import glux.tools
import glux.geometry

class Disk():

    def __init__(self,size,color1,color2=None,parts=25):

        self.size = size;

        self.height = size; #This actually half the height
        self.width = size; #This is actually half the width

        self.color1 = glux.tools.translate_color(*color1);

        if color2 == None:
            self.color2 = glux.tools.translate_color(*color1);
        else:
            self.color2 = glux.tools.translate_color(*color2);

        self.parts = parts;

    def draw(self,pos):

        #Unbind previous textures
        glBindTexture(GL_TEXTURE_2D, 0);

        #Reset the position
        glLoadIdentity()

        #Start drawing the disk
        glBegin(GL_TRIANGLE_FAN)

        #Start the with center
        basex,basey = pos;

        glColor4fv(self.color1);
        glVertex2f(basex,basey)

        #Then the vertices around the center
        glColor4fv(self.color2);

        degrees_per_part = 360 / self.parts;

        for i in range(self.parts+1):
            #Use some math to determine their location
            degrees = degrees_per_part * i;
            loc = glux.geometry.angle_to_loc((basex,basey),degrees,self.size);

            glVertex2f(*loc);

        try:
            glEnd();
        except:
            print('Error drawing circle');


class Line():

    def __init__(self,size,color):

        self.size = size;
        self.color = glux.tools.translate_color(*color);

    def draw(self,c1,c2):

        #Unbind previous textures
        glBindTexture(GL_TEXTURE_2D, 0);

        #Reset the position
        glLoadIdentity()

        glColor4fv(self.color);
        glLineWidth(self.size);

        glBegin(GL_LINES);
        glVertex2d(*c1);
        glVertex2d(*c2);

        try:
            glEnd();
        except:
            print('Error drawing line');

