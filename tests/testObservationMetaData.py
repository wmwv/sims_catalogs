from __future__ import with_statement

import os
import numpy
import unittest
import lsst.utils.tests as utilsTests
from collections import OrderedDict
from lsst.sims.catalogs.generation.db import ObservationMetaData
from lsst.sims.utils import Site

class ObservationMetaDataTest(unittest.TestCase):
    """
    This class will test that ObservationMetaData correctly assigns
    and returns its class variables (unrefractedRA, unrefractedDec, etc.)

    It will also test the behavior of the m5 member variable.
    """

    def testExceptions(self):
        """
        Test that errors are produced whenever ObservationMetaData
        parameters are overwritten in an unintentional way
        """

        metadata = {'Unrefracted_RA':[1.5], 'Unrefracted_Dec':[0.5],
                    'Opsim_expmjd':[52000.0],
                    'Opsim_rotskypos':[1.3],
                    'Opsim_filter':[2]}

        obs_metadata = ObservationMetaData(phoSimMetadata=metadata,
                                           boundType='circle',
                                           boundLength=0.1)

        with self.assertRaises(RuntimeError):
            obs_metadata.unrefractedRA=1.2

        with self.assertRaises(RuntimeError):
            obs_metadata.unrefractedDec=1.2

        with self.assertRaises(RuntimeError):
            obs_metadata.rotSkyPos=1.5

        with self.assertRaises(RuntimeError):
            obs_metadata.setBandpassAndM5()

        obs_metadata = ObservationMetaData(unrefractedRA=1.5,
                                           unrefractedDec=1.5)


    def testM5(self):
        """
        Test behavior of ObservationMetaData's m5 member variable
        """

        self.assertRaises(RuntimeError, ObservationMetaData, bandpassName='u', m5=[12.0, 13.0])
        self.assertRaises(RuntimeError, ObservationMetaData, bandpassName=['u', 'g'], m5=15.0)
        self.assertRaises(RuntimeError, ObservationMetaData, bandpassName=['u', 'g'], m5=[12.0, 13.0, 15.0])

        obsMD = ObservationMetaData()
        self.assertIsNone(obsMD.m5)

        obsMD = ObservationMetaData(bandpassName='g', m5=12.0)
        self.assertAlmostEqual(obsMD.m5['g'], 12.0, 10)

        obsMD = ObservationMetaData(bandpassName=['u','g','r'], m5=[10,11,12])
        self.assertEqual(obsMD.m5['u'], 10)
        self.assertEqual(obsMD.m5['g'], 11)
        self.assertEqual(obsMD.m5['r'], 12)


    def testM5Assignment(self):
        """
        Test assignment of M5 and bandpass in ObservationMetaData
        """
        obsMD = ObservationMetaData(bandpassName=['u','g'], m5=[12.0, 11.0])
        self.assertAlmostEqual(obsMD.m5['u'], 12.0, 10)
        self.assertAlmostEqual(obsMD.m5['g'], 11.0, 10)

        obsMD.setBandpassAndM5(bandpassName=['i','z'], m5=[25.0, 22.0])
        self.assertAlmostEqual(obsMD.m5['i'], 25.0, 10)
        self.assertAlmostEqual(obsMD.m5['z'], 22.0, 10)

        with self.assertRaises(KeyError):
            obsMD.m5['u']

        with self.assertRaises(KeyError):
            obsMD.m5['g']

        phoSimMD = {'Opsim_filter':[4]}
        obsMD.phoSimMetadata = phoSimMD
        self.assertEqual(obsMD.bandpass, 4)
        self.assertTrue(obsMD.m5 is None)


    def testDefault(self):
        """
        Test that ObservationMetaData's default variables are properly set
        """

        testObsMD = ObservationMetaData()

        self.assertEqual(testObsMD.unrefractedRA,None)
        self.assertEqual(testObsMD.unrefractedDec,None)
        self.assertAlmostEqual(testObsMD.rotSkyPos,0.0,10)
        self.assertEqual(testObsMD.bandpass,'r')
        self.assertAlmostEqual(testObsMD.site.longitude,-1.2320792,10)
        self.assertAlmostEqual(testObsMD.site.latitude,-0.517781017,10)
        self.assertAlmostEqual(testObsMD.site.height,2650,10)
        self.assertAlmostEqual(testObsMD.site.xPolar,0,10)
        self.assertAlmostEqual(testObsMD.site.yPolar,0,10)
        self.assertAlmostEqual(testObsMD.site.meanTemperature,284.655,10)
        self.assertAlmostEqual(testObsMD.site.meanPressure,749.3,10)
        self.assertAlmostEqual(testObsMD.site.meanHumidity,0.4,10)
        self.assertAlmostEqual(testObsMD.site.lapseRate,0.0065,10)

    def testSite(self):
        """
        Test that site data gets passed correctly when it is not default
        """
        testSite = Site(longitude = 2.0, latitude = -1.0, height = 4.0,
            xPolar = 0.5, yPolar = -0.5, meanTemperature = 100.0,
            meanPressure = 500.0, meanHumidity = 0.1, lapseRate = 0.1)

        testObsMD = ObservationMetaData(site=testSite)

        self.assertAlmostEqual(testObsMD.site.longitude,2.0,10)
        self.assertAlmostEqual(testObsMD.site.latitude,-1.0,10)
        self.assertAlmostEqual(testObsMD.site.height,4.0,10)
        self.assertAlmostEqual(testObsMD.site.xPolar,0.5,10)
        self.assertAlmostEqual(testObsMD.site.yPolar,-0.5,10)
        self.assertAlmostEqual(testObsMD.site.meanTemperature,100.0,10)
        self.assertAlmostEqual(testObsMD.site.meanPressure,500.0,10)
        self.assertAlmostEqual(testObsMD.site.meanHumidity,0.1,10)
        self.assertAlmostEqual(testObsMD.site.lapseRate,0.1,10)

    def testAssignment(self):
        """
        Test that ObservationMetaData member variables get passed correctly
        """

        mjd = 5120.0
        RA = 1.5
        Dec = -1.1
        rotSkyPos = -10.0
        skyBrightness = 25.0

        testObsMD = ObservationMetaData()
        testObsMD.unrefractedRA = RA
        testObsMD.unrefractedDec = Dec
        testObsMD.rotSkyPos = rotSkyPos
        testObsMD.skyBrightness = skyBrightness
        testObsMD.boundType = 'box'
        testObsMD.boundLength = [1.2, 3.0]
        testObsMD.mjd = mjd

        self.assertAlmostEqual(testObsMD.unrefractedRA, RA, 10)
        self.assertAlmostEqual(testObsMD.unrefractedDec, Dec, 10)
        self.assertAlmostEqual(testObsMD.rotSkyPos, rotSkyPos, 10)
        self.assertAlmostEqual(testObsMD.skyBrightness, skyBrightness, 10)
        self.assertEqual(testObsMD.boundType, 'box')
        self.assertAlmostEqual(testObsMD.boundLength[0],1.2, 10)
        self.assertAlmostEqual(testObsMD.boundLength[1], 3.0, 10)
        self.assertAlmostEqual(testObsMD.mjd, mjd, 10)

        #test reassignment

        testObsMD.unrefractedRA = RA+1.0
        testObsMD.unrefractedDec = Dec+1.0
        testObsMD.rotSkyPos = rotSkyPos+1.0
        testObsMD.skyBrightness = skyBrightness+1.0
        testObsMD.boundLength = 2.2
        testObsMD.boundType = 'circle'
        testObsMD.mjd = mjd + 10.0

        self.assertAlmostEqual(testObsMD.unrefractedRA, RA+1.0, 10)
        self.assertAlmostEqual(testObsMD.unrefractedDec, Dec+1.0, 10)
        self.assertAlmostEqual(testObsMD.rotSkyPos, rotSkyPos+1.0, 10)
        self.assertAlmostEqual(testObsMD.skyBrightness, skyBrightness+1.0, 10)
        self.assertEqual(testObsMD.boundType, 'circle')
        self.assertAlmostEqual(testObsMD.boundLength,2.2, 10)
        self.assertAlmostEqual(testObsMD.mjd, mjd+10.0, 10)

        phosimMD = OrderedDict([('Unrefracted_RA', (-2.0,float)),
                                ('Unrefracted_Dec', (0.9,float)),
                                ('Opsim_rotskypos', (1.1,float)),
                                ('Opsim_expmjd',(4000.0,float)),
                                ('Opsim_filter',('g',str))])


        testObsMD.phoSimMetadata = phosimMD
        self.assertAlmostEqual(testObsMD.unrefractedRA, numpy.degrees(-2.0), 10)
        self.assertAlmostEqual(testObsMD.unrefractedDec, numpy.degrees(0.9), 10)
        self.assertAlmostEqual(testObsMD.rotSkyPos, numpy.degrees(1.1))
        self.assertAlmostEqual(testObsMD.mjd, 4000.0, 10)
        self.assertAlmostEqual(testObsMD.bandpass, 'g')

        testObsMD = ObservationMetaData(mjd=mjd, unrefractedRA=RA,
            unrefractedDec=Dec, rotSkyPos=rotSkyPos, bandpassName='z',
            skyBrightness=skyBrightness)

        self.assertAlmostEqual(testObsMD.mjd,5120.0,10)
        self.assertAlmostEqual(testObsMD.unrefractedRA,1.5,10)
        self.assertAlmostEqual(testObsMD.unrefractedDec,-1.1,10)
        self.assertAlmostEqual(testObsMD.rotSkyPos,-10.0,10)
        self.assertEqual(testObsMD.bandpass,'z')
        self.assertAlmostEqual(testObsMD.skyBrightness, skyBrightness, 10)

        testObsMD = ObservationMetaData()
        testObsMD.assignPhoSimMetaData(phosimMD)

        self.assertAlmostEqual(testObsMD.mjd,4000.0,10)

        #recall that Unrefracted_RA/Dec are stored as radians in phoSim metadata
        self.assertAlmostEqual(testObsMD.unrefractedRA,numpy.degrees(-2.0),10)
        self.assertAlmostEqual(testObsMD.unrefractedDec,numpy.degrees(0.9),10)
        self.assertAlmostEqual(testObsMD.rotSkyPos,numpy.degrees(1.1),10)
        self.assertEqual(testObsMD.bandpass,'g')

        testObsMD = ObservationMetaData()
        testObsMD.phoSimMetadata = phosimMD

        self.assertAlmostEqual(testObsMD.mjd,4000.0,10)

        #recall that Unrefracted_RA/Dec are stored as radians in phoSim metadata
        self.assertAlmostEqual(testObsMD.unrefractedRA,numpy.degrees(-2.0),10)
        self.assertAlmostEqual(testObsMD.unrefractedDec,numpy.degrees(0.9),10)
        self.assertAlmostEqual(testObsMD.rotSkyPos,numpy.degrees(1.1),10)
        self.assertEqual(testObsMD.bandpass,'g')


    def testBoundBuilding(self):
        """
        Make sure ObservationMetaData can build bounds
        """
        boxBounds = [0.1, 0.3]
        circObs = ObservationMetaData(boundType='circle',unrefractedRA=0.0, unrefractedDec=0.0, boundLength=1.0)
        squareObs = ObservationMetaData(boundType = 'box',unrefractedRA=0.0, unrefractedDec=0.0, boundLength=1.0)
        boxObs = ObservationMetaData(boundType = 'box', unrefractedRA=0.0, unrefractedDec=0.0, boundLength=boxBounds)

    def testBounds(self):
        """
        Test if ObservationMetaData correctly assigns the unrefracted[RA,Dec]
        when circle and box bounds are specified
        """

        circRA = 25.0
        circDec = 50.0
        radius = 5.0

        boxRA = 15.0
        boxDec = 0.0
        boxLength = numpy.array([5.0,10.0])

        testObsMD = ObservationMetaData(boundType='circle',
                     unrefractedRA = circRA, unrefractedDec=circDec, boundLength = radius)
        self.assertAlmostEqual(testObsMD.unrefractedRA,25.0,10)
        self.assertAlmostEqual(testObsMD.unrefractedDec,50.0,10)

        testObsMD = ObservationMetaData(boundType = 'box',
                                        unrefractedRA = boxRA, unrefractedDec = boxDec, boundLength=boxLength)
        self.assertAlmostEqual(testObsMD.unrefractedRA,15.0,10)
        self.assertAlmostEqual(testObsMD.unrefractedDec,0.0,10)

def suite():
    """Returns a suite containing all the test cases in this module."""
    utilsTests.init()
    suites = []
    suites += unittest.makeSuite(ObservationMetaDataTest)

    return unittest.TestSuite(suites)

def run(shouldExit=False):
    """Run the tests"""
    utilsTests.run(suite(), shouldExit)

if __name__ == "__main__":
    run(True)
