# Display an image using wxPython
import wx
import cStringIO
import downloadingEC2CredentialsImage

global bmp

class DisplayDownloadingEC2CredentialsImage(wx.Panel):
    def __init__(self, parent, id):
        # create the panel
        wx.Panel.__init__(self, parent, id)
        bmp = downloadingEC2CredentialsImage.getDownloadingEC2CredentialsBitmap()
        wx.StaticBitmap(self, -1, bmp, (0, 0), (bmp.GetWidth(), bmp.GetHeight()))

app = wx.PySimpleApp()
bmp = downloadingEC2CredentialsImage.getDownloadingEC2CredentialsBitmap()
ec2ImageFrame = wx.Frame(None, -1, "CVL Administrator - How To Download EC2 Credentials From Nectar", size = (bmp.GetWidth(), bmp.GetHeight()))
DisplayDownloadingEC2CredentialsImage(ec2ImageFrame,-1)
ec2ImageFrame.Show(1)
app.MainLoop()

