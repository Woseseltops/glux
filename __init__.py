import math
import pygame as p
from OpenGL.GL import *
from OpenGL.GLU import *

class Window():


    def start(self,width,height):
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

        #Prepare lighting
        self.light = None;
        self.lit_up_textures = None;

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
        if source.__class__ in [Texture,Layer]:
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
        if source.__class__ in [Texture,Layer]:
            extra = source.height;
        else:
            extra = 0;

        #Calculate the shadow position
        basepoint1,basepoint2 = get_basepoints(light_location,source,dest);
        topleft = distance_to_coord_via_point(light_location,100,basepoint1);
        topright = distance_to_coord_via_point(light_location,100,basepoint2);        

        #Translate to OpenGL coords
        dest = self.translate_coords(dest,extra);
        basepoint1 = self.translate_coords(basepoint1);
        basepoint2 = self.translate_coords(basepoint2);
        topleft = self.translate_coords(topleft);
        topright = self.translate_coords(topright);

        #Draw the shadow
        source.draw_shadow(basepoint1,basepoint2,topleft,topright,dest);

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
            
    def build_lighting(self,environment_color,lights,shadowcasters):

        #First check if any lights need to be rerendered
        rerender_needed = False;

        for l,pos in lights:
            if l.last_pos != pos:
                l.render(environment_color,pos,self,shadowcasters);
                rerender_needed = True;

        #Stop building light if nothing has changed
        if not rerender_needed:
            return;

        #Blend the full renders of all lights together
        self.change_rendermode('texture');

        self.fill(environment_color);

        self.change_blendmode('screen');

        for l in lights:
            l[0].draw((0,0));

        self.change_blendmode('alpha');
        self.change_rendermode('window');

        self.light = self.render_texture;

        #Blend the light_only renders of all lights together
        self.change_rendermode('texture');

        self.fill(environment_color);

        self.change_blendmode('screen');

        for l in lights:
            l[0].draw((0,0),'light_only');

        self.change_blendmode('alpha');
        self.change_rendermode('window');

        light_only = self.render_texture;

        #Create a special texture for all shadowcasters
        transtex = create_transparent_texture(self.width,self.height);
        self.change_rendermode('texture',transtex);
        
        for shadowcaster, pos in shadowcasters:
            self.draw(shadowcaster,pos);

        #Light up the shadowcasters and save the texture
        self.change_blendmode('multiply');
        self.draw(light_only,(0,0));
        self.change_blendmode('alpha');

        self.change_rendermode('window');
        
        self.lit_up_textures = self.render_texture;

    def draw_lighting(self):

        if self.light != None:

            #Draw light and shadows on top of the world
            self.change_blendmode('multiply');
            self.draw(self.light,(0,0));
            self.change_blendmode('alpha');

            #Draw the lit up shadowcaster on top of that
            # (otherwhise the shadows would be on top of them)
            self.draw(self.lit_up_textures,(0,0));
        else:
            raise LightNotRenderedError;

class Texture():

    def __init__(self,source,colorkey=None,width=None,height=None,base=None):

        #Load the image via a pygame Surface
        if isinstance(source,str):
            current_surface = p.image.load(source);
        elif isinstance(source,p.Surface) or isinstance(source,bytes):
            current_surface = source;
        elif source == None:
            current_surface = None;

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

        #Transform to texture
        if colorkey != None:
            current_surface.set_colorkey(colorkey);
        self._surface_to_texture(current_surface);

        #Transform to displaylist
        self.texture_to_displaylist();

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

    def draw_shadow(self,basepoint1,basepoint2,topleft,topright,dest):

        #Reset the color
        glColor4fv((0,0,0,0.6));

        #Reset the position
        glLoadIdentity();

        #Travel to the coordinate
#        glTranslate(dest[0],dest[1],0);

        #Put the texture on a qaudrangle        
        self.bind();
        glBegin(GL_QUADS);        
        glTexCoord2f(0, 0); glVertex2f(*basepoint1);    # Bottom Left Of The Texture and Quad

#        glColor4fv((0,0,0,0)); #Make shadow fade away

        glTexCoord2f(0, 1); glVertex2f(*topleft);    # Top Left Of The Texture and Quad
        glTexCoord2f(1, 1); glVertex2f(*topright);    # Top Right Of The Texture and Quad

        glColor4fv((0,0,0,1));

        glTexCoord2f(1, 0); glVertex2f(*basepoint2);    # Bottom Right Of The Texture and Quad
        glEnd();

    def __del__(self):        
        glDeleteTextures(self.tex);

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

        #Calculate text width and texture width (must be dividable by 16)
        self.width = current_surface.get_width();
        self.height = current_surface.get_height();

        #Transform to texture
        self._surface_to_texture(current_surface);

        #Transform to displaylist
        self.texture_to_displaylist();

class Disk():

    def __init__(self,size,color1,color2=None):

        self.size = size;
        
        self.height = size; #This actually half the height
        self.width = size; #This is actually half the width
        
        self.color1 = color1;

        if color2 == None:
            self.color2 = color1;
        else:
            self.color2 = color2;

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

        parts = 25;
        degrees_per_part = 360 / parts;

        for i in range(parts+1):
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

        glColor4f(*self.color); 
        glLineWidth(self.size); 

        glBegin(GL_LINES);
        glVertex2d(*c1);
        glVertex2d(*c2);
        glEnd();    

class Light():

    def __init__(self,color,strength):

        self.color = color;
        self.strength = strength;
        self.disk = Disk(strength,color,(0,0,0,0));
#        self.disk = Disk(strength,color,color);
        self.tex = None;
        self.tex_light_only = None;
        self.last_pos = (None,None);

    def draw(self,pos,mode = 'full'):

        if self.tex != None:
            if mode == 'full':
                self.tex.draw(pos);
            elif mode == 'light_only':
                self.tex_light_only.draw(pos);
        else:
            raise LightNotRenderedError;

    def render(self,environment_color,pos,window,shadowcasters):

        #Manual garbage collection
        del self.tex;
        del self.tex_light_only;

        #Render the full texture
        window.change_rendermode('texture');

        window.fill(environment_color);
        window.draw(self.disk,pos);

        for caster,casterpos in shadowcasters:
            window.draw_shadow(self,pos,caster,casterpos);

        window.change_rendermode('window');

        self.tex = window.render_texture;

        #Render the light only texture
        window.change_rendermode('texture');

        window.fill(environment_color);
        window.draw(self.disk,pos);
        
        window.change_rendermode('window');

        self.tex_light_only = window.render_texture;

        #Cache this if this light's position doesn't change
        self.last_pos = pos;
        

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

def distance_to_coord_via_point(start,distance,via):

    angle = coords_to_angle(start,via);
    angle = turn_around_degrees(angle,90);    
    pos = angle_to_loc(via,angle,distance);

    return pos;

def create_transparent_texture(width,height):

    white_pixel = b'\xff\xff\xff\xff';
    transparent_pixel = b'\xff\x00\xb4\x00';
    s = (width*height)*transparent_pixel;
    
    return Texture(s,width=width,height=height);

def translate_color(r,g,b,a):
    return (r/255,g/255,b/255,a/255);

def get_basepoints(light_location,source,dest):

    if source.base == None:
        basepoint1 = (dest[0],dest[1]+source.height);
        basepoint2 = (dest[0]+source.width,dest[1]+source.height);
    else:

        if light_location[0] < dest[0] + source.base.left:
            hor = 'left';
        elif light_location[0] > dest[0]  + source.base.left \
             and light_location[0] < dest[0] + source.base.right:
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
            basepoint1 = (dest[0]+source.base.right,dest[1]+source.base.top);
            basepoint2 = (dest[0]+source.base.left,dest[1]+source.base.bottom);
        elif hor == 'mid' and ver == 'top':
            basepoint1 = (dest[0]+source.base.left,dest[1]+source.base.top);
            basepoint2 = (dest[0]+source.base.right,dest[1]+source.base.top);
        elif hor == 'right' and ver == 'top':
            basepoint1 = (dest[0]+source.base.left,dest[1]+source.base.top);
            basepoint2 = (dest[0]+source.base.right,dest[1]+source.base.bottom);

        elif hor == 'left' and ver == 'mid':
            basepoint2 = (dest[0]+source.base.left,dest[1]+source.base.top);
            basepoint1 = (dest[0]+source.base.left,dest[1]+source.base.bottom);
        elif hor == 'mid' and ver == 'mid':
            basepoint1 = (dest[0],dest[1]+source.height);
            basepoint2 = (dest[0]+source.width,dest[1]+source.height);           
        elif hor == 'right' and ver == 'mid':
            basepoint1 = (dest[0]+source.base.right,dest[1]+source.base.top);
            basepoint2 = (dest[0]+source.base.right,dest[1]+source.base.bottom);

        elif hor == 'left' and ver == 'bot':
            basepoint1 = (dest[0]+source.base.left,dest[1]+source.base.top);
            basepoint2 = (dest[0]+source.base.right,dest[1]+source.base.bottom);
        elif hor == 'mid' and ver == 'bot':
            basepoint1 = (dest[0]+source.base.left,dest[1]+source.base.bottom);
            basepoint2 = (dest[0]+source.base.right,dest[1]+source.base.bottom);
        elif hor == 'right' and ver == 'bot':
            basepoint1 = (dest[0]+source.base.right,dest[1]+source.base.top);
            basepoint2 = (dest[0]+source.base.left,dest[1]+source.base.bottom);
  
    return basepoint1, basepoint2

class LightNotRenderedError(Exception):
    pass;

#Probleem
# Build-lighting moet gecleaned worden
# Licht moet geoptimizeerd worden (veel shadowcasters = traag?);

# Layer kan alleen nog met Textures omgaan
# Layers verplaatsen?
# Bij iedere keer dat je een disk drawt, moeten alle vertices opnieuw uitgerekend worden

# Als je text drawt direct voor een shape, verschijnt de shape niet
# Alles omzetten naar color4fv in plaats van met *
# Kleurvertaler (van buiten allen pygame-kleuren gebruiken)

#Requirements
# Light: base (voor zowel dikte als breedte), raampjes, schaduwen op elkaar laten vallen
# Screenshots
# Textblocks
# Animation
