import os
import unittest
import lsst.utils.tests as utilsTests
from collections import OrderedDict
from lsst.sims.catalogs.generation.db import ObservationMetaData, Site

class ObservationMetaDataTest(unittest.TestCase):
    """
    This class will test that ObservationMetaData correctly assigns
    and returns its class variables (UnrefractedRA, UnrefractedDec, etc.)
    """
    
    def testDefault(self):
        testObsMD = ObservationMetaData()
        
        self.assertAlmostEqual(testObsMD.UnrefractedRA,0.0,10)
        self.assertAlmostEqual(testObsMD.UnrefractedDec,-0.5,10)
        self.assertAlmostEqual(testObsMD.RotSkyPos,0.0,10)
        self.assertEqual(testObsMD.bandpass,'i')
        
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
        mjd = 5120.0
        RA = 1.5
        Dec = -1.1
        RotSkyPos = -0.2
        
        testObsMD = ObservationMetaData(mjd=mjd, UnrefractedRA=RA,
            UnrefractedDec=Dec, RotSkyPos=RotSkyPos, bandpassName = 'z')
        
        self.assertAlmostEqual(testObsMD.mjd,5120.0,10)
        self.assertAlmostEqual(testObsMD.UnrefractedRA,1.5,10)
        self.assertAlmostEqual(testObsMD.UnrefractedDec,-1.1,10)
        self.assertAlmostEqual(testObsMD.RotSkyPos,-0.2,10)
        self.assertEqual(testObsMD.bandpass,'z')
        
        phosimMD = OrderedDict([('Unrefracted_RA', (-2.0,float)), 
                                ('Unrefracted_Dec', (0.9,float)),
                                ('Opsim_rotskypos', (1.1,float)), 
                                ('Opsim_expmjd',(4000.0,float)),
                                ('Opsim_filter',(1,int))])
        
        testObsMD.assignPhoSimMetaData(phosimMD)
        
        self.assertAlmostEqual(testObsMD.mjd,4000.0,10)
        self.assertAlmostEqual(testObsMD.UnrefractedRA,-2.0,10)
        self.assertAlmostEqual(testObsMD.UnrefractedDec,0.9,10)
        self.assertAlmostEqual(testObsMD.RotSkyPos,1.1,10)
        self.assertEqual(testObsMD.bandpass,'g')

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
