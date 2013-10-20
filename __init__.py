import math
import os
import pygame as p
from OpenGL.GL import *
from OpenGL.GLU import *

class Window():

    def start(self,width,height,environment_color=False):
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
            self.env_color = translate_color(*environment_color);

        #Prepare lighting
        self.light = None;
        self.inside = False;
        self.shadowcasters = [];
        self.white_shadowcasters = None;

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
            dest2 = self._translate_coords(dest2,extra);            
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
        
    def change_rendermode(self,new_mode,use_texture = None):

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
                self.render_texture = Texture(None,width=self.width,height=self.height);
            else:
                self.render_texture = use_texture;
            self.render_texture.bind();

            #Link it to the buffer (try again if memory problem)
            while True:
                try:
                    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.render_texture.tex, 0);
                    break;
                except:
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
            
    def build_lighting(self,lights,glowers):

        #Blend the renders of all lights together
        self.change_rendermode('texture');

        self.fill(self.env_color);

        self.change_blendmode('screen');

        for l in lights:
            l.draw((0,0));

        self.change_blendmode('alpha');
        self.change_rendermode('window');

        self.light = self.render_texture;

    def draw_lighting(self):

        if self.light != None:

            #Draw light and shadows on top of the world
            self.change_blendmode('multiply');
            self.draw(self.light,(0,0));
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
        
class Texture():

    def __init__(self,source,colorkey=None,width=None,height=None,base=None,square_shadow=False):

        #Load the image via a pygame Surface
        if isinstance(source,str):
            current_surface = p.image.load(source).convert();
        elif isinstance(source,p.Surface) or isinstance(source,bytes):
            current_surface = source;
        elif source == None:
            current_surface = None;

        #Save some properties
        self.square_shadow = square_shadow
        self.white_variant = None;
        
        if width != None:
            self.width = width;
        else:
            self.width = current_surface.get_width();

        if height != None:
            self.height = height;
        else:
            self.height = current_surface.get_height();

        if base == None:
            self.base = None;
        else:
            self.base = p.Rect(*base);

        if self.height > self.width:
            self.longest_side = self.height;        
        else:
            self.longest_side = self.width;        

        #Transform to texture
        if colorkey != None:
            current_surface.set_colorkey(colorkey);
        self._surface_to_texture(current_surface);

        #Transform to displaylist
        self.texture_to_displaylist();

    def get_center(self,loc):

        return (loc[0] + self.width / 2, loc[1] + self.height / 2);

    def _surface_to_texture(self,surface):

        #Turn it into a string
        if surface == None:
            texturedata = 0;
        elif isinstance(surface,bytes):
            texturedata = surface;
        else:
            texturedata = p.image.tostring(surface, "RGBA", 1);

        #Create an OpenGL texture
        self.tex = glGenTextures(1); #create
        self.bind();

        #Some settings
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR); #Pretty upscaling
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR); #Pretty downscaling        

        #Put the surface in
        if surface != None:
            glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texturedata );
        else:
            glTexImage2D( GL_TEXTURE_2D, 0, GL_RGB, self.width, self.height, 0, GL_RGB, GL_UNSIGNED_BYTE, None )        

    def texture_to_displaylist(self):

        #Create displaylist
        self.list = glGenLists(1);

        #Bind the displaylist
        glNewList(self.list,GL_COMPILE);

        #Put the texture on a qaudrangle        
        self.bind();
        glBegin(GL_QUADS);        
        glTexCoord2f(0, 0); glVertex2f(0, 0);    # Bottom Left Of The Texture and Quad
        glTexCoord2f(0, 1); glVertex2f(0, self.height);    # Top Left Of The Texture and Quad
        glTexCoord2f(1, 1); glVertex2f(self.width, self.height);    # Top Right Of The Texture and Quad
        glTexCoord2f(1, 0); glVertex2f(self.width, 0);    # Bottom Right Of The Texture and Quad

        #Finish
        glEnd();
        glEndList();        

    def bind(self):
        """We're talking about this texture from now on""";
        
        glBindTexture(GL_TEXTURE_2D, self.tex);

    def unbind(self): #Non tested
        
        glBindTexture(GL_TEXTURE_2D, 0);

    def draw(self,dest):

        #Reset the color
        glColor4fv((1,1,1,1));

        #Reset the position
        glLoadIdentity();

        #Travel to the coordinate
        glTranslate(dest[0],dest[1],0);

        #Draw the displaylist
        glCallList(self.list);

    def save(self,filename):

        #Save glux.Texture to pygame.Surface
        self.bind();
        pixels = glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE);
        surface = p.image.fromstring(pixels, (self.width, self.height), "RGBA")

        #Undo the accidental mirroring and rotating
        surface = p.transform.rotate(surface,180);
        surface = p.transform.flip(surface,True,False);

        #Save        
        p.image.save(surface, filename)
        
    def draw_shadow(self,basepoint1,basepoint2,topleft,topright,dest,inside):

        #Reset the color
        if inside:
            glColor4fv((0,0,0,1));
        else:
            glColor4fv((0,0,0,0.6));

        #Reset the position
        glLoadIdentity();

        #Travel to the coordinate
#        glTranslate(dest[0],dest[1],0);

        #Put the texture on a qaudrangle        
        if self.square_shadow:
            glBegin(GL_QUADS);        
            glVertex2f(*basepoint1);
            glVertex2f(*topleft);
            glVertex2f(*topright);
            glVertex2f(*basepoint2);
        else:
            self.bind();
            glBegin(GL_QUADS);        
            glTexCoord2f(0, 0); glVertex2f(*basepoint1);    # Bottom Left Of The Texture and Quad

            if not inside:
                glColor4fv((0,0,0,0)); #Make shadow fade away

            glTexCoord2f(0, 1); glVertex2f(*topleft);    # Top Left Of The Texture and Quad
            glTexCoord2f(1, 1); glVertex2f(*topright);    # Top Right Of The Texture and Quad

            if not inside:
                glColor4fv((0,0,0,1));

            glTexCoord2f(1, 0); glVertex2f(*basepoint2);    # Bottom Right Of The Texture and Quad

        glEnd();

    def give_white_variant(self):

        if self.white_variant == None:
            self.bind();
            colored_pixels = glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE);
            white_pixels = b'';

            white_pixel = b'\xff\xff\xff\xff';
            transparent_pixel = b'\x00\x00\x00\x00';

            nr = 0;
            
            for b in colored_pixels:

                if nr == 3:

                    if b == 0:
                        white_pixels += transparent_pixel;
                    else:
                        white_pixels += white_pixel;

                nr += 1;
                if nr > 3:
                    nr = 0;

            self.white_variant = Texture(white_pixels,width=self.width,height=self.height,
                                         base=self.base,square_shadow=self.square_shadow);

        return self.white_variant;

    def __del__(self):        
        glDeleteTextures(self.tex);

class Animation():

    def __init__(self,name,speed,path=None):

        """Speed can go from 0 to 100"""

        self.unique_frames = [];
        self.frames = [];

        if path == None:
            files = os.listdir();
        else:
            files = os.listdir(path);

        for f in files:
            if name in f:
                if path==None:
                    file_loc = f;
                else:
                    file_loc = path+'/'+f;
                self.unique_frames.append(Texture(file_loc));

        for uf in self.unique_frames:
            for i in range(101-speed):
                self.frames.append(uf);

        self.current_frame = 0;
        self.paused = False;

        self.height = self.frames[0].height;
        self.width = self.frames[0].width;        

    def tick(self):
        self.current_frame += 1;

        if self.current_frame + 1 > len(self.frames):
            self.current_frame = 0;

    def draw(self,dest):
        self.frames[self.current_frame].draw(dest);

    def pause(self):
        self.paused = True;

    def unpause(self):
        self.paused = False;

class Layer():

    def __init__(self,window):

        self.window = window;
        self.width = 0;
        self.height = 0;

        #Create displaylist
        self.glist = glGenLists(1);

        #Save the textures
        self.textures = [];

        self.frozen = False;

    def append(self,material,location=None):

        if location != None:
            material = [(material,location)];

        for i in material:
            self.textures.append(i);

    def freeze(self):

        #Bind the displaylist
        glNewList(self.glist,GL_COMPILE);

        for texture, dest in self.textures:
            #Put the texture on a quadrangle        
            texture.bind(); 

            dest = self.window.translate_coords(dest,texture.height);
            glLoadIdentity();
            glTranslate(dest[0],dest[1],0);

            glBegin(GL_QUADS);        
            glTexCoord2f(0, 0); glVertex2f(0, 0);    # Bottom Left Of The Texture and Quad
            glTexCoord2f(0, 1); glVertex2f(0, texture.height);    # Top Left Of The Texture and Quad
            glTexCoord2f(1, 1); glVertex2f(texture.width, texture.height);    # Top Right Of The Texture and Quad
            glTexCoord2f(1, 0); glVertex2f(texture.width, 0);    # Bottom Right Of The Texture and Quad

            #Finish
            glEnd();

            #See if you need to be bigger
            if texture.height > self.height:
                self.height = texture.height;

            if texture.width > self.width:
                self.widht = texture.width;
            
        glEndList();                

        self.frozen = True;

    def draw(self,dest):

        if self.frozen:
            #Reset the color
            glColor4fv((1,1,1,1));

            #Reset the position
            glLoadIdentity();

            #Travel to the coordinate
            glTranslate(0,0,0);

            #Draw the displaylist
            glCallList(self.glist);                

class Text(Texture):

    def __init__(self,text,font,color):

        #Text to surface
        current_surface = font.render(text, True, color)

        #Calculate text width and texture width
        self.width = current_surface.get_width();
        self.height = current_surface.get_height();

        #Transform to texture
        self._surface_to_texture(current_surface);

        #Transform to displaylist
        self.texture_to_displaylist();

class Textblock(Texture):

    def __init__(self,text,font,color,width,center=False):

        self.font = font;
        self.width = width;
        self.color = color;
        self.text = text;
        self.center = center;

        #Will be calculated later
        self.lines = [''];
        self.images = [];
        self.height = 0;

        self._text_to_lines();
        self._lines_to_images();
        
    def _text_to_lines(self):

        words = self.text.split();
        current_line = 0;
        
        for w in words:

            #How long will the line be with this word added?
            if self.lines[current_line] == '':
                trying_out_text = w;
            else:
                trying_out_text = self.lines[current_line] + ' ' + w;            

            #If within block, add it
            if self.font.size(trying_out_text)[0] < self.width:
                self.lines[current_line] = trying_out_text;

            #Else, start a new line
            else:
                self.lines.append(w);
                current_line += 1;

    def _lines_to_images(self):

        self.height = 0;

        for l in self.lines:
            t = Text(l,self.font,self.color);
            self.images.append(t);

            #Get the highest line height
            if t.height > self.height:
                self.height = t.height;

    def draw(self,dest):

        x, y = dest;
        original_x = x;

        for i in self.images:
            if self.center:
                x = round(original_x + (self.width - i.width) / 2);

            i.draw((x,y));
            y -= self.height;

class Glower(Texture):

    def __init__(self,source,color=None,colorkey=None):

        #Load the image via a pygame Surface
        if isinstance(source,str):
            current_surface = p.image.load(source);
        elif isinstance(source,p.Surface) or isinstance(source,bytes):
            current_surface = source;
        elif source == None:
            current_surface = None;

        #Set some properties
        self.width = current_surface.get_width();
        self.height = current_surface.get_height();

        if color == None:
            color = (255,255,255,255);

        #Recolor in the glowing color
        current_surface.fill(color);

        #Transform to texture
        if colorkey != None:
            current_surface.set_colorkey(colorkey);
        self._surface_to_texture(current_surface);

        #Transform to displaylist
        self.texture_to_displaylist();

class Disk():

    def __init__(self,size,color1,color2=None,parts=25):

        self.size = size;
        
        self.height = size; #This actually half the height
        self.width = size; #This is actually half the width
        
        self.color1 = translate_color(*color1);

        if color2 == None:
            self.color2 = translate_color(*color1);
        else:
            self.color2 = translate_color(*color2);

        self.parts = parts;

    def draw(self,pos):
        
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
            loc = angle_to_loc((basex,basey),degrees,self.size);
            
            glVertex2f(*loc);

        glEnd()    

class Line():

    def __init__(self,size,color):

        self.size = size;
        self.color = color;

    def draw(self,c1,c2):

        #Reset the position
        glLoadIdentity()    

        glColor4fv(self.color); 
        glLineWidth(self.size); 

        glBegin(GL_LINES);
        glVertex2d(*c1);
        glVertex2d(*c2);
        glEnd();    

class Light():

    def __init__(self,color,strength,shadows):

        self.color = color;
        self.strength = strength;
        self.visibility_distance = strength * 0.5;
        self.shadows = shadows;
        
        self.disk = Disk(strength,color,(0,0,0,0));
#        self.disk = Disk(strength,color,color);
        self.tex = None;

    def draw(self,pos):

        if self.tex != None:
            self.tex.draw(pos);
        else:
            raise LightNotRenderedError;

    def render(self,pos,window):

        #Manual garbage collection
        del self.tex;

        #Render shadowlayer
        transtex = create_transparent_texture(window.width,window.height); #Start with empty tex
        window.change_rendermode('texture',transtex);

        if self.shadows:

            #Draw shadows
            for caster,casterpos in window.shadowcasters:
                if distance(pos,caster.get_center(casterpos)) < \
                   self.visibility_distance + caster.longest_side:
                    window.draw_shadow(self,pos,caster,casterpos);

            window.draw_white_shadowcasters();

        window.change_rendermode('window');
        shadowtex = window.render_texture;

        #Render this light
        window.change_rendermode('texture');

        window.fill(window.env_color);
        window.draw(self.disk,pos);

        #Put the shadowlayer on top        
        window.change_blendmode('multiply'); 
        window.draw(shadowtex,(0,0));
        window.change_blendmode('alpha');

        window.change_rendermode('window');

        self.tex = window.render_texture;
        del shadowtex;

def angle_to_loc(startloc,angle,distance):

    x = math.sin(math.radians(angle)) * distance; #Lenght of the opposite side of the triangle
    y = math.cos(math.radians(angle)) * distance; #Length of the adjacent side of the triangle

    return startloc[0] + x, startloc[1] + y;

def coords_to_angle(c1,c2):

    adj = c2[0] - c1[0];
    opp = c2[1] - c1[1];

    try:
        tan = opp / adj;
    except ZeroDivisionError:
        tan = opp;

    if tan == 0 and c1[0] > c2[0]:
        tan = 0.01;

    degrees = math.degrees(math.atan(tan));

    #Reform
    degrees *= -1;

    #Invert negatives, so that -90 becomes 180
    if degrees < 0:
        degrees+= 180;

    #Lower part of the circle should be inverted again    
    if c2[1] > c1[1]:
        degrees += 180;

    return degrees;
    
def turn_around_degrees(angle,add):

    angle += add;
    if angle > 359:
        angle-= 360;

    return angle;

def distance(x,y):
    """Pythogorian distance""";

    a = x[0] - y[0];
    b = x[1] - y[1];

    return math.sqrt(a*a+b*b);

def distance_to_coord_via_point(start,distance,via):

    angle = coords_to_angle(start,via);
    angle = turn_around_degrees(angle,90);    
    pos = angle_to_loc(via,angle,distance);

    return pos;

def create_transparent_texture(width,height):

    white_pixel = b'\xff\xff\xff\xff';
    transparent_pixel = b'\xff\xff\xff\x00';
    s = (width*height)*transparent_pixel;
    
    return Texture(s,width=width,height=height);

def translate_color(r,g,b,a):
    return (r/255,g/255,b/255,a/255);

def get_basepoints(light_location,source,dest):

    if source.base == None:
        basepoint1 = (dest[0],dest[1]+source.height);
        basepoint2 = (dest[0]+source.width,dest[1]+source.height);
    else:

        basetop = source.base.top;
        basebottom = source.base.bottom;

        if source.square_shadow:
            baseleft = source.base.left;
            baseright = source.base.right;
        else:
            baseleft = 0;
            baseright = source.width;

        if light_location[0] < dest[0]:
            hor = 'left';
        elif light_location[0] > dest[0] \
             and light_location[0] < dest[0] + source.width:
            hor = 'mid';
        else:
            hor = 'right';

        if light_location[1] < dest[1] + source.base.top:
            ver = 'top';
        elif light_location[1] > dest[1]  + source.base.top \
             and light_location[1] < dest[1] + source.base.bottom:
            ver = 'mid';
        else:
            ver = 'bot';

        if hor == 'left' and ver == 'top':
            basepoint1 = (dest[0]+baseright,dest[1]+source.base.top);
            basepoint2 = (dest[0]+baseleft,dest[1]+source.base.bottom);
        elif hor == 'mid' and ver == 'top':
            basepoint1 = (dest[0]+baseleft,dest[1]+source.base.top);
            basepoint2 = (dest[0]+baseright,dest[1]+source.base.top);
        elif hor == 'right' and ver == 'top':
            basepoint1 = (dest[0]+baseleft,dest[1]+source.base.top);
            basepoint2 = (dest[0]+baseright,dest[1]+source.base.bottom);

        elif hor == 'left' and ver == 'mid':
            basepoint2 = (dest[0]+baseleft,dest[1]+source.base.top);
            basepoint1 = (dest[0]+baseright,dest[1]+source.base.bottom);
        elif hor == 'mid' and ver == 'mid':
            basepoint1 = (dest[0]+baseleft,dest[1]+source.height);
            basepoint2 = (dest[0]+baseright,dest[1]+source.height);           
        elif hor == 'right' and ver == 'mid':
            basepoint1 = (dest[0]+baseright,dest[1]+source.base.top);
            basepoint2 = (dest[0]+baseright,dest[1]+source.base.bottom);

        elif hor == 'left' and ver == 'bot':
            basepoint1 = (dest[0]+baseleft,dest[1]+source.base.top);
            basepoint2 = (dest[0]+baseright,dest[1]+source.base.bottom);
        elif hor == 'mid' and ver == 'bot':
            basepoint1 = (dest[0]+baseleft,dest[1]+source.base.bottom);
            basepoint2 = (dest[0]+baseright,dest[1]+source.base.bottom);
        elif hor == 'right' and ver == 'bot':
            basepoint1 = (dest[0]+baseright,dest[1]+source.base.top);
            basepoint2 = (dest[0]+baseleft,dest[1]+source.base.bottom);
  
    return basepoint1, basepoint2

def is_texturelike(o):

    if o.__class__ in [Texture,Text,Glower,Layer,Animation,Textblock]:
        return True;
    else:
        return False;

class LightNotRenderedError(Exception):
    pass;

#Probleem
# Layer kan alleen nog met Textures omgaan
# Layers verplaatsen?
# Shape (zoals disk) verschijnt niet als je direct daarvoor iets met alpha hebt gedrawed

#Requirements
# Light: schaduwen op elkaar laten vallen
