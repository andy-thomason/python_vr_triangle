import time
import sdl2
import openvr
import numpy

from OpenGL.GL import *
from OpenGL.GL.shaders import compileShader, compileProgram
from openvr.glframework import shader_string
from sdl2 import *

class OpenVRTest(object):
  "Tiny OpenVR example with python (based on openvr example)"

  def __init__(s):
    s.vr_system = openvr.init(openvr.VRApplication_Scene)
    s.vr_compositor = openvr.VRCompositor()
    poses_t = openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount
    s.poses = poses_t()
    s.w, s.h = s.vr_system.getRecommendedRenderTargetSize()
    SDL_Init(SDL_INIT_VIDEO)
    s.window = SDL_CreateWindow (b"test",
      SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
      100, 100, SDL_WINDOW_SHOWN|SDL_WINDOW_OPENGL)
    s.context = SDL_GL_CreateContext(s.window)
    SDL_GL_MakeCurrent(s.window, s.context)
    s.depth_buffer = glGenRenderbuffers(1)
    s.frame_buffers = glGenFramebuffers(2)
    s.texture_ids = glGenTextures(2)
    s.textures = [None] * 2
    s.eyes = [openvr.Eye_Left, openvr.Eye_Right] 
    s.cameraToProjection = [None] * 2
    s.headToCamera = [None] * 2
    s.col3 = [0, 0, 0, 1]

    vertexShader = compileShader(
      shader_string(
        """
          layout (location=0) uniform mat4 cameraToProjection;
          layout (location=1) uniform mat4 modelToCamera;
          void main() {
            float angle = gl_VertexID * (3.14159*2/3);
            vec4 modelPos = vec4(cos(angle), sin(angle), -2, 1);
            gl_Position = cameraToProjection * (modelToCamera * modelPos);
          }
        """
      ),
      GL_VERTEX_SHADER
    )
    fragmentShader = compileShader(
      shader_string(
        """
          out vec4 colour;
          void main() {
            colour = vec4(1, 0, 0, 1);
          }
        """
      ),
      GL_FRAGMENT_SHADER
    )
    s.program = compileProgram(vertexShader, fragmentShader)
    s.vertexBuffer = glGenVertexArrays(1)

    for eye in range(2):
      glBindFramebuffer(GL_FRAMEBUFFER, s.frame_buffers[eye])
      glBindRenderbuffer(GL_RENDERBUFFER, s.depth_buffer)
      glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, s.w, s.h)
      glFramebufferRenderbuffer(
        GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER,
        s.depth_buffer)
      glBindTexture(GL_TEXTURE_2D, s.texture_ids[eye])
      glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGBA8, s.w, s.h, 0, GL_RGBA, GL_UNSIGNED_BYTE,
        None)
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
      glFramebufferTexture2D(
        GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D,
        s.texture_ids[eye], 0)
      texture = openvr.Texture_t()
      texture.handle = int(s.texture_ids[eye])
      texture.eType = openvr.TextureType_OpenGL
      texture.eColorSpace = openvr.ColorSpace_Gamma
      s.textures[eye] = texture
      proj = s.vr_system.getProjectionMatrix(s.eyes[eye], 0.2, 500.0)
      s.cameraToProjection[eye] = numpy.matrix(
        [ [proj.m[i][j] for i in range(4)] for j in range(4) ],
        numpy.float32
      )
      camToHead = s.vr_system.getEyeToHeadTransform(s.eyes[eye])
      s.headToCamera[eye] = numpy.matrix(
        [ [camToHead.m[i][j] for i in range(3)] + [s.col3[j]] for j in range(4) ],
        numpy.float32
      ).I

  def draw(s):
    s.vr_compositor.waitGetPoses(s.poses, openvr.k_unMaxTrackedDeviceCount, None, 0)
    headPose = s.poses[openvr.k_unTrackedDeviceIndex_Hmd]
    if not headPose.bPoseIsValid:
      return True

    headToWorld = headPose.mDeviceToAbsoluteTracking
    worldToHead =  numpy.matrix(
      [ [headToWorld.m[i][j] for i in range(3)] + [s.col3[j]] for j in range(4) ],
      numpy.float32
    ).I

    for eye in range(2):
      modelToCamera = s.headToCamera[eye] * worldToHead

      glBindFramebuffer(GL_FRAMEBUFFER, s.frame_buffers[eye])
      glClearColor(0.5, 0.5, 0.5, 0.0)
      glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
      glViewport(0, 0, s.w, s.h)
      glBindVertexArray(s.vertexBuffer)
      glEnable(GL_DEPTH_TEST)
      
      glUseProgram(s.program)
      glUniformMatrix4fv(0, 1, False, numpy.asarray(s.cameraToProjection[eye]))
      glUniformMatrix4fv(1, 1, False, numpy.asarray(modelToCamera))
      glDrawArrays(GL_TRIANGLES, 0, 3)
      s.vr_compositor.submit(s.eyes[eye], s.textures[eye])
    return True

if __name__ == "__main__":
  print("kill with ctrl-C (no frills here!)")
  test = OpenVRTest()
  while test.draw():
    pass


