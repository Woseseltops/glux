import math

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

def turn_around_degrees(angle,add):

    angle += add;
    if angle > 359:
        angle-= 360;

    return angle;

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
