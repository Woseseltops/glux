import pygame as p
from OpenGL.GL import *
from OpenGL.GLU import *
import glux.texture
import os

class Texture():

    def __init__(self,source,colorkey=None,width=None,height=None,base=None,square_shadow=False,transparent=False):

        #Load the image via a pygame Surface
        if isinstance(source,str):
            if not transparent:
                current_surface = p.image.load(source).convert();
            else:
                current_surface = p.image.load(source).convert_alpha();

        elif isinstance(source,p.Surface) or isinstance(source,bytes):
            current_surface = source;
        elif source == None:
            current_surface = None;

        #Save some properties
        self._alpha = 1;
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

    @property
    def alpha(self):

        return self._alpha;

    @alpha.setter
    def alpha(self,value):

        if value != self._alpha:
            self._alpha = value;
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

        #Reset the color
        glColor4fv((1,1,1,self._alpha));

        #Put the texture on a qaudrangle
        self.bind();

        #Point sprites
#        glBegin(GL_POINTS);
#        glTexCoord2f(0, 0);
#        glVertex3f(0.0, 0.0,0);

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

    def draw(self,dest,rotation=None):

        #Reset the position
        glLoadIdentity();

        #Travel to the coordinate
        glTranslate(dest[0],dest[1],0);

        if rotation != None:
            centerx = 56;
            centery = 56;
            glTranslatef(centerx,centery,0);
            glRotate(rotation,0,0,-1);
            glTranslatef(-centerx,-centery,0);

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
        glTranslate(dest[0],dest[1],0);

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

    def get_rect(self):

        return p.Rect(0,0,self.width,self.height)

    def __del__(self):
        glDeleteTextures(self.tex);

class Animation():

    def __init__(self,name,speed,path=None,colorkey=None):

        """Speed can go from 0 to 100"""

        self._alpha = 1;
        self.unique_frames = [];
        self.frames = [];

        if path == None:
            files = os.listdir();
        else:
            files = os.listdir(path);

        files.sort();

        for f in files:
            if name in f:
                if path==None:
                    file_loc = f;
                else:
                    file_loc = path+'/'+f;
                self.unique_frames.append(Texture(file_loc,colorkey=colorkey));

        for uf in self.unique_frames:
            for i in range(101-speed):
                self.frames.append(uf);

        self.current_frame = 0;
        self.paused = False;

        self.height = self.frames[0].height;
        self.width = self.frames[0].width;

    def get_rect(self):

        return p.Rect(0,0,self.width,self.height)

    def tick(self):

        """Changes which frame is the current frame, returns whether this is another image""";

        old = self.frames[self.current_frame];

        if not self.paused:
            self.current_frame += 1;

            if self.current_frame + 1 > len(self.frames):
                self.current_frame = 0;

        new = self.frames[self.current_frame];

        if old == new:
            return False;
        else:
            return True;

    def draw(self,dest,rotation=None):
        self.frames[self.current_frame].draw(dest);

    def pause(self):
        self.paused = True;

    def unpause(self):
        self.paused = False;

    @property
    def alpha(self):

        return self._alpha;

    @alpha.setter
    def alpha(self,value):

        for frame in self.frames:
            frame.alpha = value;

        self._alpha = value;

class Layer():

    def __init__(self,window):

        self.window = window;
        self.width = 0;
        self.height = 0;

        #Save the textures
        self.textures = [];

        self.glist = None;
        self.frozen = False;
        self.pointer_pos = (0,0);

    def append(self,material,location=None):

        if location != None:
            material = [(material,location)];

        for i in material:
            self.textures.append(i);

    def _add_tex_to_displaylist(self,texture,dest):

        #Put the texture on a quadrangle
        texture.bind();

        dest = self.window.translate_coords(dest,texture.height);

        x_diff = dest[0] - self.pointer_pos[0];
        y_diff = dest[1] - self.pointer_pos[1];

        glTranslate(x_diff,y_diff,0);
        self.pointer_pos = dest;

        glBegin(GL_QUADS);
        glTexCoord2f(0, 0); glVertex2f(0, 0);    # Bottom Left Of The Texture and Quad
        glTexCoord2f(0, 1); glVertex2f(0, texture.height);    # Top Left Of The Texture and Quad
        glTexCoord2f(1, 1); glVertex2f(texture.width, texture.height);    # Top Right Of The Texture and Quad
        glTexCoord2f(1, 0); glVertex2f(texture.width, 0);    # Bottom Right Of The Texture and Quad

        #Finish
        glEnd();

    def freeze(self):

        glLoadIdentity();
        self.pointer_pos = (0,0);

        displaylist_created = False;

        while not displaylist_created:
            try:
                #Create displaylist
                self.glist = glGenLists(1);

                #Bind the displaylist
                glNewList(self.glist,GL_COMPILE);
                displaylist_created = True;
            except:
                print('Warning: OpenGL displaylist creation error')

        for texture, dest in self.textures:

            if not isinstance(texture,Textblock):
                self._add_tex_to_displaylist(texture, dest);

                #See if you need to be bigger
                if texture.height > self.height:
                    self.height = texture.height;

                if texture.width > self.width:
                    self.width = texture.width;
            else:
                x, y = dest;
                original_x = x;

                for i in texture.images:
                    if texture.center:
                        x = round(original_x + (texture.width - i.width) / 2);

                    self._add_tex_to_displaylist(i,(x,y));

                    #See if you need to be bigger
                    if i.height > self.height:
                        self.height = i.height;

                    if texture.width > self.width:
                        self.width = texture.width;

                    y += texture.height;

        glEndList();

        self.frozen = True;

    def draw(self,dest,rotation=None):

        if self.frozen:
            #Reset the color
            glColor4fv((1,1,1,1));

            #Reset the position
            glLoadIdentity();

            #Travel to the coordinate
            glTranslate(dest[0],dest[1],0);

            #Draw the displaylist
            glCallList(self.glist);

class Text(Texture):

    def __init__(self,text,font,color):

        self._alpha = 1;

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

        self._alpha = 1;
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

        self.lines = [''];
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
        self.images = [];

        for l in self.lines:
            t = Text(l,self.font,self.color);
            self.images.append(t);

            #Get the highest line height
            if t.height > self.height:
                self.height = t.height;

    def change_text(self,newtext):
        """Freeze text into image again""";

        self.text = newtext;

        self._text_to_lines();
        self._lines_to_images();

    @property
    def alpha(self):

        return self._alpha;

    @alpha.setter
    def alpha(self,value):

        self._alpha = value;

        for i in self.images:
            i.alpha = self._alpha;

    def draw(self,dest,rotation=None):

        x, y = dest;
        original_x = x;

        for i in self.images:
            if self.center:
                x = round(original_x + (self.width - i.width) / 2);

            i.draw((x,y));
            y -= self.height;

    def __del__(self):

        for i in self.images:
            del i;

def create_transparent_texture(width,height):

    white_pixel = b'\xff\xff\xff\xff';
    transparent_pixel = b'\xff\xff\xff\x00';
    s = (width*height)*transparent_pixel;

    return Texture(s,width=width,height=height);

def is_texturelike(o):

    if o.__class__ in [Texture,Text,glux.light.Glower,Animation,Textblock]:
        return True;
    else:
        return False;
