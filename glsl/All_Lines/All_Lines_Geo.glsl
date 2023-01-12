layout(lines) in;
layout(triangle_strip, max_vertices = 64) out;

in VERT_OUT {
    float weight;
    float offset;
    vec4 color;
    int rounded;
    mat4 objectMatrix;
} verts[];

uniform mat4 ModelViewProjectionMatrix;
uniform vec2 Viewport;
uniform vec2 Paper;
uniform vec4 camera_coord1;
uniform vec4 camera_coord2; // camera aligned coords 1BU apart in x
uniform int res;
uniform float scale;
uniform float is_camera;

const float PI = 3.1415926;
const float INCH_TO_CM = 2.54;
const float BU_TO_IN = 100.0 / INCH_TO_CM;
out vec2 mTexCoord;
out vec4 g_color;
out float alpha;

float extAmount = 0.0;
vec4 vecOffset = vec4(0.0,0.0,verts[0].offset,0.0);
float radius = 1.0;

vec2 pxVec = vec2(1.0/Viewport.x,1.0/Viewport.y);
float view_ratio_x = Viewport.x / Viewport.y;
float view_ratio_y = Viewport.y / Viewport.x;

float min_size_fac = 4.0;
float minLength = min_size_fac*length(pxVec);

float get_ss_inch(){
    vec4 camera_proj_1 = ModelViewProjectionMatrix * camera_coord1;
    vec4 camera_proj_2 = ModelViewProjectionMatrix * camera_coord2;

    vec2 cam_ss1 = camera_proj_1.xy / camera_proj_1.w;
    vec2 cam_ss2 = camera_proj_2.xy / camera_proj_2.w;

    float ss_dist = length(cam_ss2 - cam_ss1); // this is 1BU in ss
    float ss_inch = ss_dist * BU_TO_IN; // this is 1 in in ss
    return ss_inch;
}

float ss_inch = get_ss_inch();
float ss_pt = ss_inch / 72 * scale;

float get_ss_width_from_ws(){
    mat4 inv_proj_mat = inverse(ModelViewProjectionMatrix);
    vec4 p1ss = vec4(0.0,0.0,0.0,1.0);
    vec4 p2ss = vec4(1.0,0.0,0.0,1.0);
    vec4 p1ws = inv_proj_mat * p1ss;
    vec4 p2ws = inv_proj_mat * p2ss;
    p1ws.xyz *= p1ws.w;
    p2ws.xyz *= p2ws.w;
    float ws_dist_x = length((p2ws.xyz)- (p1ws.xyz));
    return 1.0/ws_dist_x * view_ratio_x*scale;
}

float ws_ratio = get_ss_width_from_ws();

vec3 get_line_width_and_alpha(vec2 normal, float width) {
    vec2 offsetvec = vec2(normal);
    if (is_camera==1.0){
        offsetvec *= ss_pt * width;
    }
    
    float alpha = 1.0;
    if (length(offsetvec) < minLength){
        alpha *= (length(offsetvec)/minLength);
        offsetvec = normalize(offsetvec);
        offsetvec *= minLength;
    }
    offsetvec *=pxVec;
    clamp(alpha,1.0,1.0);
    return vec3(offsetvec,alpha);
}


void main() {
    // Calculate world space line normal and extension
    vec4 p1 =  gl_in[0].gl_Position;
    vec4 p2 =  gl_in[1].gl_Position;

    vec4 dir3d = vec4(normalize(p2.xyz-p1.xyz),0);

    vec4 p1ExtLocal = vec4(p1 - dir3d*extAmount);
    vec4 p2ExtLocal = vec4(p2 + dir3d*extAmount);

    // Project to Clip space Using Object and veiw matrix
    vec4 p1worldPos = verts[0].objectMatrix * p1ExtLocal;
    vec4 p1project = ModelViewProjectionMatrix * p1worldPos;

    vec4 p2worldPos =  verts[0].objectMatrix * p2ExtLocal;
    vec4 p2project = ModelViewProjectionMatrix * p2worldPos;

    // Add Z offset
    vec4 p1Ext = p1project + vecOffset;
    vec4 p2Ext = p2project + vecOffset;

    // Get Screen Space points
    vec2 ssp1 = vec2(p1Ext.xy / p1Ext.w);
    vec2 ssp2 = vec2(p2Ext.xy / p2Ext.w);

    // Get Width per point
    float width1 = verts[0].weight;
    float width2 = verts[1].weight;

    // Screen Space direction and normal
    vec2 dir = normalize(ssp2 - ssp1);
    vec2 normal = vec2(-dir[1], dir[0]);
    normal = normalize(normal);

    // Screen Space line width offset
    vec3 wa1 = get_line_width_and_alpha(normal,width1);
    vec2 lineOffset1 = wa1.xy;
    float alpha1 = wa1[2];

    vec3 wa2 = get_line_width_and_alpha(normal,width2);
    vec2 lineOffset2 = wa2.xy;
    float alpha2 = wa2[2];

    // Generate the rectangle Coords
    vec4 coords[4];
    vec2 texCoords[4];
    float alphas[4];

    coords[0] = vec4((ssp1 + lineOffset1)*p1Ext.w,p1Ext.z,p1Ext.w);
    texCoords[0] = vec2(0,1);
    alphas[0] = alpha1;

    coords[1] = vec4((ssp1 - lineOffset1)*p1Ext.w,p1Ext.z,p1Ext.w);
    texCoords[1] = vec2(0,0);
    alphas[1] = alpha1;

    coords[2] = vec4((ssp2 + lineOffset2)*p2Ext.w,p2Ext.z,p2Ext.w);
    texCoords[2] = vec2(1,1);
    alphas[2] = alpha2;

    coords[3] = vec4((ssp2 - lineOffset2)*p2Ext.w,p2Ext.z,p2Ext.w);
    texCoords[3] = vec2(1,0);
    alphas[3] = alpha2;

    // Draw Point pass
    // Get Center Point in Screen Space
    radius = 1.0;
    if (is_camera==1.0){
       radius *= ss_pt * width1;
    }
    if (verts[0].rounded==1){
        vec4 worldPos =  verts[0].objectMatrix * p1;
        vec4 project = ModelViewProjectionMatrix * worldPos;

        vec4 pointCenter = project + vecOffset;
        vec2 sspC = vec2(pointCenter.xy / pointCenter.w);

        // Get number of segments in the circle
        int segments = 28;
        
        // Generate Circle
        gl_Position = pointCenter;
        g_color = verts[0].color;
        alpha = 1.0;
        mTexCoord = vec2(0.0,0.5);
        EmitVertex();

        for (int i = 0; i <= segments; i++) {
            // Angle between each side in radians
            float ang = PI * 2.0 / float(segments) * float(i);

            // Offset from center of point
            vec2 circleOffset = vec2(cos(ang)*radius, -sin(ang)*radius);
            circleOffset.x /= Viewport.x;
            circleOffset.y /= Viewport.y;
            mTexCoord = vec2(0.0,1.0);
            gl_Position = vec4((sspC + circleOffset)*pointCenter.w, pointCenter.z, pointCenter.w);
            alpha = alpha1;
            g_color = verts[0].color;
            EmitVertex();

            g_color = verts[0].color;
            alpha = alpha1;
            gl_Position = pointCenter;
            mTexCoord = vec2(0,0.5);
            EmitVertex();
        }

        EndPrimitive();

    }

    // Draw Rectange
    for (int i = 0; i < 4; ++i) {
        mTexCoord = texCoords[i];
        gl_Position = coords[i];
        alpha = alphas[i];
        g_color = verts[0].color;
        EmitVertex();
    }
    EndPrimitive();
}