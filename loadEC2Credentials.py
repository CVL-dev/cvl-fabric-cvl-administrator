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

import wx
import StringIO

application = wx.PySimpleApp()

# Create a list of filters

# This should be fairly simple to follow, so no explanation is necessary

filters = 'EC2 Credentials files (*.zip)|*.zip'

dialog = wx.FileDialog ( None, message = 'Open something....', wildcard = filters, style = wx.OPEN)

if dialog.ShowModal() == wx.ID_OK:

    # We'll have to make room for multiple files here

    selected = dialog.GetPath()

    print 'Selected:', selected

    import zipfile

    zf = zipfile.ZipFile(selected)
    ec2rcFilename = 'ec2rc.sh'
    try:
        info = zf.getinfo(ec2rcFilename)
    except KeyError:
        print 'ERROR: Did not find %s in zip file' % ec2rcFilename
    else:
        #print '%s is %d bytes' % (info.filename, info.file_size)
        ec2rcContents = zf.read(ec2rcFilename)
        stringBuffer = StringIO.StringIO(ec2rcContents)

        line = "\n"
        ec2_access_key = ""
        ec2_secret_key = ""
        while line!="":
            line = stringBuffer.readline()
            if "export EC2_ACCESS_KEY" in line:
                lineSplit = line.split("=")
                ec2_access_key = lineSplit[1].strip()
                print "EC2_ACCESS_KEY = " + ec2_access_key
            if "export EC2_SECRET_KEY" in line:
                lineSplit = line.split("=")
                ec2_secret_key = lineSplit[1].strip()
                print "EC2_SECRET_KEY = " + ec2_secret_key

        import boto
        from boto.ec2.connection import EC2Connection
        from boto.ec2.regioninfo import RegionInfo

        region = RegionInfo(name="NeCTAR", endpoint="nova.rc.nectar.org.au")
        connection = boto.connect_ec2(aws_access_key_id=ec2_access_key,
            aws_secret_access_key=ec2_secret_key,
            is_secure=False,
            region=region,
            port=8773,
            path="/services/Cloud")

        reservations = connection.get_all_instances()
        print reservations

        keypairs = connection.get_all_key_pairs()
        print keypairs
        print keypairs[0].name

        security_groups = connection.get_all_security_groups()
        print security_groups

        images = connection.get_all_images()
        #.print images
        #print images[0].name

        from pprint import pprint
        #pprint(images[0].__dict__)

        centosImage = None
        for image in images:
            # ami-0000000d Centos 6.2 amd64
            if image.id=="ami-0000000d":
                centosImage = image
                print "Found CentOS image: " + centosImage.id + ", " + centosImage.name

else:

    print 'Nothing was selected.'

dialog.Destroy()

