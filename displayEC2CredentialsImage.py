#  CVL Administrator - A GUI for launching/managing NeCTAR instances.
#  Copyright (C) 2012  James Wettenhall, Monash University
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  Enquires: James.Wettenhall@monash.edu or help@massive.org.au

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

