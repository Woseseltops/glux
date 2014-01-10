import math
import os
import pygame as p
from OpenGL.GL import *
from OpenGL.GLU import *
import OpenGL.platform.win32
import OpenGL.arrays.ctypesarrays
import OpenGL.arrays.lists
import OpenGL.arrays.numbers
import OpenGL.arrays.strings
import OpenGL.arrays.nones

#Glux package
from glux.texture import *
from glux.shape import *
from glux.geometry import *
from glux.light import *
import glux.tools

class Window():

    def start(self,width,height,caption,environment_color=False):
        #Creates the acutal window
        p.display.set_mode((width,height),p.OPENGL|p.DOUBLEBUF);

        #Load the window
        glViewport(0, 0, width, height);

        #Set the 2D mode        
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();

        gluOrtho2D(0,width,0,height);

        #?
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        self.width = width;
        self.height = height;

        #Turn on smooth shading
        glShadeModel(GL_SMOOTH);

        #Default background color
        glClearColor(0.0,0.0,0.0,1.0);

        #Start depth buffer
        glClearDepth(1.0);

        #Enable textures
        glEnable(GL_TEXTURE_2D);

        #Alpha staat standaard aan
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        #Render mode mode
        self.render_to = 'window';
        self.render_texture = Texture(None,width=self.width,height=self.height);
        self.framebuffer = None;

        #Environment color
        if not environment_color:
            self.env_color = (0,0,0,0);
        else:
            self.env_color = glux.tools.translate_color(*environment_color);

        #Prepare lighting
        self.light = {};
        self.inside = False;
        self.shadowcasters = [];
        self.white_shadowcasters = None;

        #Caption
        p.display.set_caption(caption)

    def close(self):
        p.display.quit();

    def update(self):
        p.display.flip();

    def draw_empty_background(self):
        self.fill((0,0,0,0));

    def fill(self,color):
        glClearColor(*color);
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()        
        
    def draw(self,source,dest1, dest2=None): 

        #pygame to opengl coordinates
        if is_texturelike(source):
            extra = source.height;
        else:
            extra = 0;

        dest1 = self.translate_coords(dest1,extra);

        #Draw
        if dest2 == None:
            source.draw(dest1);
        else:
            dest2 = self.translate_coords(dest2,extra);            
            source.draw(dest1,dest2);

    def draw_shadow(self, light, light_location, source, dest):

        #pygame to opengl coordinates
        if is_texturelike(source):
            extra = source.height;
        else:
            extra = 0;

        #Calculate the shadow position
        if self.inside:
            length = source.height * 10;
        else:
            length = source.height * 2;
            
        basepoint1,basepoint2 = get_basepoints(light_location,source,dest);
        topleft = distance_to_coord_via_point(light_location,length,basepoint1);
        topright = distance_to_coord_via_point(light_location,length,basepoint2);        

        #Translate to OpenGL coords
        dest = self.translate_coords(dest,extra);
        basepoint1 = self.translate_coords(basepoint1);
        basepoint2 = self.translate_coords(basepoint2);
        topleft = self.translate_coords(topleft);
        topright = self.translate_coords(topright);

        #Draw the shadow
        source.draw_shadow(basepoint1,basepoint2,topleft,topright,dest,self.inside);

    def translate_coords(self,coords,extra = 0):

        y = self.height - coords[1] - extra;
        return (coords[0],y);
        
    def change_rendermode(self,new_mode,use_texture=None, width=None, height=None):

        if width == None:
            width = self.width;

        if height == None:
            height = self.height;

        if new_mode == self.render_to:
            return;

        if new_mode == 'texture':            

            #Explicit garbage colleciton
            if self.framebuffer != None:
                glDeleteFramebuffers(self.framebuffer)

            del self.render_texture;

            #Create the framebuffer (the target)
            self.framebuffer = glGenFramebuffers(1);
            glBindFramebuffer(GL_FRAMEBUFFER, self.framebuffer);

            #Create a new render_texture to render to
            if use_texture == None:
                self.render_texture = Texture(None,width=width,height=height);
            else:
                self.render_texture = use_texture;
            self.render_texture.bind();

            #Link it to the buffer (try again if memory problem)
            while True:
                try:
                    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.render_texture.tex, 0);
                    break;
                except:
                    print('Warning: texture creation error')
                    pass;
            
            self.render_texture.unbind();
    
            #Setup the drawbuffer (?)
            #drawbuffer = glDrawBuffers(1,GL_COLOR_ATTACHMENT0);               

            self.render_to = 'texture';

        elif new_mode == 'window':

            #Assuming you was in texture mode before, unbind the framebuffer
            glBindFramebuffer(GL_FRAMEBUFFER, 0);

            #Make a new displaylist for the newly generated texture
            self.render_texture.texture_to_displaylist();

            self.render_to = 'window';

    def change_blendmode(self,new_mode):

        if new_mode == self.render_to:
            return;

        if new_mode == 'alpha':
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        elif new_mode == 'multiply':
            glBlendFunc(GL_DST_COLOR,GL_ZERO);

        elif new_mode == 'screen':
            glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_COLOR)            
            
    def build_lighting(self,lights,glowers,width=None,height=None, key='main'):

        if width == None:
            width = self.width;

        if height == None:
            height = self.height;

        #Blend the renders of all lights together
        self.change_rendermode('texture',width=width,height=height);

        self.fill(self.env_color);

        self.change_blendmode('screen');

        for l in lights:
            l.draw((0,0));

        self.change_blendmode('alpha');
        self.change_rendermode('window');

        self.light[key] = self.render_texture;

    def draw_lighting(self, pos = None, key = 'main'):

        if pos == None:
            pos = (0,0);

        if self.light != {}:

            #Draw light and shadows on top of the world
            self.change_blendmode('multiply');
            self.draw(self.light[key],pos);
            self.change_blendmode('alpha');

        else:
            raise LightNotRenderedError;

    def set_shadowcasters(self,shadowcasters):

        self.shadowcasters = shadowcasters;

        #Create or recreate a layer for them
        self.white_shadowcasters = Layer(self);

        for caster,casterpos in self.shadowcasters:
            self.white_shadowcasters.append(caster.give_white_variant(),casterpos);

        self.white_shadowcasters.freeze();        

    def draw_white_shadowcasters(self):

        self.draw(self.white_shadowcasters,(0,0));

#Probleem
# Layer kan alleen nog met Textures omgaan
# Layers verplaatsen?

#Requirements
# Light: schaduwen op elkaar laten vallen
