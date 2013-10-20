import glux.texture
import glux.geometry
from glux.shape import Disk

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
        transtex = glux.texture.create_transparent_texture(window.width,window.height); #Start with empty tex
        window.change_rendermode('texture',transtex);

        if self.shadows:

            #Draw shadows
            for caster,casterpos in window.shadowcasters:
                if glux.geometry.distance(pos,caster.get_center(casterpos)) < \
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

class Glower(glux.texture.Texture):

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

class LightNotRenderedError(Exception):
    pass;