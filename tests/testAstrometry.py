"""
This unit test compares the outputs of the PALPY driven Astrometry
routines with outputs generated by the same routines powered by
pySLALIB v 1.0.2

There will be some difference, as the two libraries are based on slightly
different conventions (for example, the prenut routine which calculates
the matrix of precession and nutation is based on the IAU 2006A/2000
standard in PALPY and on SF2001 in pySLALIB; however, the two outputs
still agree to within one part in 10^5)

To recreate test data, install pyslalib from

https://git@github.com:/scottransom/pyslalib

include the line

from pyslalib import slalib as sla

at the top of

/lsst/sims/catalogs/measures/astrometry/Astrometry.py

and then replace all occurrences of 

pal.medthodName(args)

with

sla.sla_methodName(args)

"""

import numpy

import os
import unittest
import warnings
import sys
import lsst.utils.tests as utilsTests

from lsst.sims.catalogs.measures.instance import InstanceCatalog, compound, cached
from lsst.sims.catalogs.generation.db import DBObject, ObservationMetaData
from lsst.sims.catalogs.measures.astrometry.Astrometry import Astrometry
from lsst.sims.catalogs.measures.astrometry.Site import Site

class testCatalog(InstanceCatalog,Astrometry):
    """
    This generates a catalog class that has the bare minimum of features
    to be able to run the methods from the Astrometry mixin
    """
    catalog_type = 'MISC'
    default_columns=[('Opsim_expmjd',5000.0,float)]    
    def db_required_columns(self):
        return ['Unrefracted_Dec'],['Opsim_altitude']

class astrometryUnitTest(unittest.TestCase):

    obsMD = DBObject.from_objid('opsim3_61')
    obs_metadata=obsMD.getObservationMetaData(88544919, 0.1, makeCircBounds=True)
    cat=testCatalog(obsMD,obs_metadata=obs_metadata)    
    tol=1.0e-5
    
    def testPassingOfSite(self):
        """
        Test that site information is correctly passed to 
        InstanceCatalog objects
        """
        
        testSite=Site(longitude=10.0,latitude=20.0,height=4000.0, \
              xPolar=2.4, yPolar=1.4, meanTemperature=314.0, \
              meanPressure=800.0,meanHumidity=0.9, lapseRate=0.01)
        
        cat2=testCatalog(self.obsMD,obs_metadata=self.obs_metadata,site=testSite)
        
        self.assertEqual(cat2.site.longitude,10.0)
        self.assertEqual(cat2.site.latitude,20.0)
        self.assertEqual(cat2.site.height,4000.0)
        self.assertEqual(cat2.site.xPolar,2.4)
        self.assertEqual(cat2.site.yPolar,1.4)
        self.assertEqual(cat2.site.meanTemperature,314.0)
        self.assertEqual(cat2.site.meanPressure,800.0)
        self.assertEqual(cat2.site.meanHumidity,0.9)
        self.assertEqual(cat2.site.lapseRate,0.01)
    
    def testSphericalToCartesian(self):
        arg1=2.19911485751
        arg2=5.96902604182
        output=self.cat.sphericalToCartesian(arg1,arg2)
        
        vv=numpy.zeros((3),dtype=float)
        vv[0]=numpy.cos(arg2)*numpy.cos(arg1)
        vv[1]=numpy.cos(arg2)*numpy.sin(arg1)
        vv[2]=numpy.sin(arg2)

        self.assertAlmostEqual(output[0],vv[0],7)
        self.assertAlmostEqual(output[1],vv[1],7)
        self.assertAlmostEqual(output[2],vv[2],7)

    def testCartesianToSpherical(self):
        """
        Note that xyz[i][j] is the ith component of the jth vector
        
        Each column of xyz is a vector
        """
        xyz=numpy.zeros((3,3),dtype=float)
         
        xyz[0][0]=-1.528397655830016078e-03 
        xyz[0][1]=-1.220314328441649110e+00 
        xyz[0][2]=-1.209496845057127512e+00
        xyz[1][0]=-2.015391452804179195e+00 
        xyz[1][1]=3.209255728096233051e-01 
        xyz[1][2]=-2.420049632697228503e+00
        xyz[2][0]=-1.737023855580406284e+00 
        xyz[2][1]=-9.876134719050078115e-02 
        xyz[2][2]=-2.000636201137401038e+00
        
        output=self.cat.cartesianToSpherical(xyz)
        
        vv=numpy.zeros((3),dtype=float)
        
        for i in range(3):

            rr=numpy.sqrt(xyz[0][i]*xyz[0][i]+xyz[1][i]*xyz[1][i]+xyz[2][i]*xyz[2][i])

            vv[0]=rr*numpy.cos(output[1][i])*numpy.cos(output[0][i])
            vv[1]=rr*numpy.cos(output[1][i])*numpy.sin(output[0][i])
            vv[2]=rr*numpy.sin(output[1][i])
    
            for j in range(3):
                self.assertAlmostEqual(vv[j],xyz[j][i],7)


    def testAngularSeparation(self):
        arg1 = 7.853981633974482790e-01 
        arg2 = 3.769911184307751517e-01 
        arg3 = 5.026548245743668986e+00 
        arg4 = -6.283185307179586232e-01
        
        output=self.cat.angularSeparation(arg1,arg2,arg3,arg4)
        
        self.assertAlmostEqual(output,2.162615946398791955e+00,10)
    
    def testRotationMatrixFromVectors(self):
        v1=numpy.zeros((3),dtype=float)
        v2=numpy.zeros((3),dtype=float)
        v3=numpy.zeros((3),dtype=float)
        
        v1[0]=-3.044619987218469825e-01 
        v2[0]=5.982190522311925385e-01
        v1[1]=-5.473550908956383854e-01 
        v2[1]=-5.573565912346714057e-01 
        v1[2]=7.795545496018386755e-01 
        v2[2]=-5.757495946632366079e-01
        
        output=self.cat.rotationMatrixFromVectors(v1,v2)
        
        for i in range(3):
            for j in range(3):
                v3[i]+=output[i][j]*v1[j] 
        
        for i in range(3):
            self.assertAlmostEqual(v3[i],v2[i],7)

    def testApplyPrecession(self):
    
        ra=numpy.zeros((3),dtype=float)
        dec=numpy.zeros((3),dtype=float)
        
        ra[0]=2.549091039839124218e+00 
        dec[0]=5.198752733024248895e-01
        ra[1]=8.693375673649429425e-01 
        dec[1]=1.038086165642298164e+00
        ra[2]=7.740864769302191473e-01 
        dec[2]=2.758053025017753179e-01
        
        output=self.cat.applyPrecession(ra,dec)
        self.assertAlmostEqual(output[0][0],2.514361575034799401e+00,6)
        self.assertAlmostEqual(output[1][0], 5.306722463159389003e-01,6)
        self.assertAlmostEqual(output[0][1],8.224493314855578774e-01,6)
        self.assertAlmostEqual(output[1][1],1.029318353760459104e+00,6)
        self.assertAlmostEqual(output[0][2],7.412362765815005972e-01,6)
        self.assertAlmostEqual(output[1][2],2.662034339930458571e-01,6)
    
    def testApplyProperMotionException(self):
        """
        Make sure that applyProperMotion throws an exception
        if parallax<0.00045
        """
        
        ra=[numpy.pi/4.0]
        dec=[numpy.pi/4.0]
        pm_ra=[0.0001]
        pm_dec=[0.0001]
        parallax=[0.0002]
        v_rad=[10.0]
        
        self.assertRaises(ValueError,self.cat.applyProperMotion,\
                          ra,dec,pm_ra,pm_dec,parallax,v_rad)
    
    def testApplyProperMotion(self):
    
        ra=numpy.zeros((3),dtype=float)
        dec=numpy.zeros((3),dtype=float)
        pm_ra=numpy.zeros((3),dtype=float)
        pm_dec=numpy.zeros((3),dtype=float)
        parallax=numpy.zeros((3),dtype=float)
        v_rad=numpy.zeros((3),dtype=float)
        
        ra[0]=2.549091039839124218e+00 
        dec[0]=5.198752733024248895e-01 
        pm_ra[0]=-8.472633255615005918e-05 
        pm_dec[0]=-5.618517146980475171e-07 
        parallax[0]=9.328946209650547383e-02 
        v_rad[0]=3.060308412186171267e+02 
         
        ra[1]=8.693375673649429425e-01 
        dec[1]=1.038086165642298164e+00 
        pm_ra[1]=-5.848962163813087908e-05 
        pm_dec[1]=-3.000346282603337522e-05 
        parallax[1]=5.392364722571952457e-02 
        v_rad[1]=4.785834687356999098e+02 
        
        ra[2]=7.740864769302191473e-01 
        dec[2]=2.758053025017753179e-01 
        pm_ra[2]=5.904070507320858615e-07 
        pm_dec[2]=-2.958381482198743105e-05 
        parallax[2]=2.172865273161764255e-02 
        v_rad[2]=-3.225459751425886452e+02
        
        ep=2.001040286039033845e+03 
        mjd=2.018749109074271473e+03 
        
        output=self.cat.applyProperMotion(ra,dec,pm_ra,pm_dec,parallax,v_rad,EP0=ep,MJD=mjd)
        
        self.assertAlmostEqual(output[0][0],2.549309127917495754e+00,6) 
        self.assertAlmostEqual(output[1][0],5.198769294314042888e-01,6)
        self.assertAlmostEqual(output[0][1],8.694881589882680339e-01,6) 
        self.assertAlmostEqual(output[1][1],1.038238225568303363e+00,6)
        self.assertAlmostEqual(output[0][2],7.740849573146946216e-01,6) 
        self.assertAlmostEqual(output[1][2],2.758844356561930278e-01,6)

    def testEquatorialToGalactic(self):
    
        ra=numpy.zeros((3),dtype=float)
        dec=numpy.zeros((3),dtype=float)
        
        ra[0]=2.549091039839124218e+00 
        dec[0]=5.198752733024248895e-01
        ra[1]=8.693375673649429425e-01 
        dec[1]=1.038086165642298164e+00
        ra[2]=7.740864769302191473e-01 
        dec[2]=2.758053025017753179e-01
        
        output=self.cat.equatorialToGalactic(ra,dec)
        
        self.assertAlmostEqual(output[0][0],3.452036693523627964e+00,6) 
        self.assertAlmostEqual(output[1][0],8.559512505657201897e-01,6)
        self.assertAlmostEqual(output[0][1],2.455968474619387720e+00,6) 
        self.assertAlmostEqual(output[1][1],3.158563770667878468e-02,6)
        self.assertAlmostEqual(output[0][2],2.829585540991265358e+00,6) 
        self.assertAlmostEqual(output[1][2],-6.510790587552289788e-01,6)


    def testGalacticToEquatorial(self):
        
        lon=numpy.zeros((3),dtype=float)
        lat=numpy.zeros((3),dtype=float)
        
        lon[0]=3.452036693523627964e+00 
        lat[0]=8.559512505657201897e-01
        lon[1]=2.455968474619387720e+00 
        lat[1]=3.158563770667878468e-02
        lon[2]=2.829585540991265358e+00 
        lat[2]=-6.510790587552289788e-01
        
        output=self.cat.galacticToEquatorial(lon,lat)
        
        self.assertAlmostEqual(output[0][0],2.549091039839124218e+00,6) 
        self.assertAlmostEqual(output[1][0],5.198752733024248895e-01,6)
        self.assertAlmostEqual(output[0][1],8.693375673649429425e-01,6) 
        self.assertAlmostEqual(output[1][1],1.038086165642298164e+00,6)
        self.assertAlmostEqual(output[0][2],7.740864769302191473e-01,6) 
        self.assertAlmostEqual(output[1][2],2.758053025017753179e-01,6)

    def testApplyMeanApparentPlace(self):
    
        ra=numpy.zeros((3),dtype=float)
        dec=numpy.zeros((3),dtype=float)
        pm_ra=numpy.zeros((3),dtype=float)
        pm_dec=numpy.zeros((3),dtype=float)
        parallax=numpy.zeros((3),dtype=float)
        v_rad=numpy.zeros((3),dtype=float)
        
    
        ra[0]=2.549091039839124218e+00 
        dec[0]=5.198752733024248895e-01 
        pm_ra[0]=-8.472633255615005918e-05 
        pm_dec[0]=-5.618517146980475171e-07 
        parallax[0]=9.328946209650547383e-02 
        v_rad[0]=3.060308412186171267e+02

        ra[1]=8.693375673649429425e-01 
        dec[1]=1.038086165642298164e+00 
        pm_ra[1]=-5.848962163813087908e-05 
        pm_dec[1]=-3.000346282603337522e-05 
        parallax[1]=5.392364722571952457e-02 
        v_rad[1]=4.785834687356999098e+02
        
        ra[2]=7.740864769302191473e-01 
        dec[2]=2.758053025017753179e-01 
        pm_ra[2]=5.904070507320858615e-07 
        pm_dec[2]=-2.958381482198743105e-05 
        parallax[2]=2.172865273161764255e-02 
        v_rad[2]=-3.225459751425886452e+02
        
        ep=2.001040286039033845e+03 
        mjd=2.018749109074271473e+03
        
        output=self.cat.applyMeanApparentPlace(ra,dec,pm_ra,pm_dec,parallax,v_rad,Epoch0=ep,MJD=mjd)
        
        self.assertAlmostEqual(output[0][0],2.525858337335585180e+00,6) 
        self.assertAlmostEqual(output[1][0],5.309044018653210628e-01,6)
        self.assertAlmostEqual(output[0][1],8.297492370691380570e-01,6) 
        self.assertAlmostEqual(output[1][1],1.037400063009288331e+00,6)
        self.assertAlmostEqual(output[0][2],7.408639821342507537e-01,6) 
        self.assertAlmostEqual(output[1][2],2.703229189890907214e-01,6)

    def testApplyMeanObservedPlace(self):
        """
        Note: this routine depends on Aopqk which fails if zenith distance
        is too great (or, at least, it won't warn you if the zenith distance
        is greater than pi/2, in which case answers won't make sense)
        """
    
        ra=numpy.zeros((3),dtype=float)
        dec=numpy.zeros((3),dtype=float)
    
        ra[0]=2.549091039839124218e+00 
        dec[0]=5.198752733024248895e-01
        ra[1]=4.346687836824714712e-01 
        dec[1]=-5.190430828211490821e-01
        ra[2]=7.740864769302191473e-01 
        dec[2]=2.758053025017753179e-01
        
        mjd=2.018749109074271473e+03
        
        output=self.cat.applyMeanObservedPlace(ra,dec,MJD=mjd)
        
        self.assertAlmostEqual(output[0][0],2.547475965605183745e+00,6) 
        self.assertAlmostEqual(output[1][0],5.187045152602967057e-01,6)
       
        self.assertAlmostEqual(output[0][1],4.349858626308809040e-01,6) 
        self.assertAlmostEqual(output[1][1],-5.191213875880701378e-01,6)
        
        self.assertAlmostEqual(output[0][2],7.743528611421227614e-01,6) 
        self.assertAlmostEqual(output[1][2],2.755070101670137328e-01,6)
        
        output=self.cat.applyMeanObservedPlace(ra,dec,MJD=mjd,altAzHr=True)
        
        self.assertAlmostEqual(output[0][0],2.547475965605183745e+00,6) 
        self.assertAlmostEqual(output[1][0],5.187045152602967057e-01,6) 
        self.assertAlmostEqual(output[2][0],1.168920017932007643e-01,6) 
        self.assertAlmostEqual(output[3][0],8.745379535264000692e-01,6)
        
        self.assertAlmostEqual(output[0][1],4.349858626308809040e-01,6) 
        self.assertAlmostEqual(output[1][1],-5.191213875880701378e-01,6) 
        self.assertAlmostEqual(output[2][1],6.766119585479937193e-01,6) 
        self.assertAlmostEqual(output[3][1],4.433969998336554141e+00,6)
        
        self.assertAlmostEqual(output[0][2],7.743528611421227614e-01,6) 
        self.assertAlmostEqual(output[1][2],2.755070101670137328e-01,6) 
        self.assertAlmostEqual(output[2][2],5.275840601437552513e-01,6)
        self.assertAlmostEqual(output[3][2],5.479759580847959555e+00,6)
        
        output=self.cat.applyMeanObservedPlace(ra,dec,MJD=mjd,includeRefraction=False)
        
        self.assertAlmostEqual(output[0][0],2.549091783674975353e+00,6) 
        self.assertAlmostEqual(output[1][0],5.198746844679964507e-01,6)
        
        self.assertAlmostEqual(output[0][1],4.346695674418772359e-01,6) 
        self.assertAlmostEqual(output[1][1],-5.190436610150490626e-01,6)
        
        self.assertAlmostEqual(output[0][2],7.740875471580924705e-01,6) 
        self.assertAlmostEqual(output[1][2],2.758055401087299296e-01,6)
        
        output=self.cat.applyMeanObservedPlace(ra,dec,MJD=mjd,includeRefraction=False,altAzHr=True)
        
        self.assertAlmostEqual(output[0][0],2.549091783674975353e+00,6) 
        self.assertAlmostEqual(output[1][0],5.198746844679964507e-01,6) 
        self.assertAlmostEqual(output[2][0],1.150652107618796299e-01,6) 
        self.assertAlmostEqual(output[3][0],8.745379535264000692e-01,6)
        
        self.assertAlmostEqual(output[0][1],4.346695674418772359e-01,6) 
        self.assertAlmostEqual(output[1][1],-5.190436610150490626e-01,6) 
        self.assertAlmostEqual(output[2][1],6.763265401447272618e-01,6) 
        self.assertAlmostEqual(output[3][1],4.433969998336554141e+00,6)
        
        self.assertAlmostEqual(output[0][2],7.740875471580924705e-01,6)      
        self.assertAlmostEqual(output[1][2],2.758055401087299296e-01,6) 
        self.assertAlmostEqual(output[2][2],5.271912536356709866e-01,6) 
        self.assertAlmostEqual(output[3][2],5.479759580847959555e+00,6)


    def testApplyApparentToTrim(self):
        
        ra=numpy.zeros((3),dtype=float)
        dec=numpy.zeros((3),dtype=float)
    
        ra[0]=2.549091039839124218e+00 
        dec[0]=5.198752733024248895e-01
        ra[1]=4.346687836824714712e-01 
        dec[1]=-5.190430828211490821e-01
        ra[2]=7.740864769302191473e-01 
        dec[2]=2.758053025017753179e-01
        
        mjd=2.018749109074271473e+03
        
        output=self.cat.applyApparentToTrim(ra,dec,MJD=mjd,altAzHr=True)        
        
        self.assertAlmostEqual(output[0][0],2.549091783674975353e+00,6)
        self.assertAlmostEqual(output[1][0],5.198746844679964507e-01,6)
        self.assertAlmostEqual(output[0][1],4.346695674418772359e-01,6)
        self.assertAlmostEqual(output[1][1],-5.190436610150490626e-01,6)
        self.assertAlmostEqual(output[0][2],7.740875471580924705e-01,6)
        self.assertAlmostEqual(output[1][2],2.758055401087299296e-01,6)
        self.assertAlmostEqual(output[2],5.271914342095551653e-01,6)
        self.assertAlmostEqual(output[3],5.479759402150099490e+00,6)

    def testRefractionCoefficients(self):
        output=self.cat.refractionCoefficients()
        
        self.assertAlmostEqual(output[0],2.295817926320665320e-04,6) 
        self.assertAlmostEqual(output[1],-2.385964632924575670e-07,6)

    def testApplyRefraction(self):
        coeffs=self.cat.refractionCoefficients()
       
        output=self.cat.applyRefraction(0.25*numpy.pi,coeffs[0],coeffs[1])
        
        self.assertAlmostEqual(output,7.851689251070859132e-01,6)

    def testCalcLast(self):
            
        arg1=2.004031374869656474e+03 
        arg2=10
        
        output=self.cat.calcLast(arg1,arg2)
        self.assertAlmostEqual(output,1.662978602873423029e+00,5) 

    def testEquatorialToHorizontal(self):
        arg1=2.549091039839124218e+00 
        arg2=5.198752733024248895e-01 
        arg3=2.004031374869656474e+03
        output=self.cat.equatorialToHorizontal(arg1,arg2,arg3)
        
        self.assertAlmostEqual(output[0],4.486633480937949336e-01,5) 
        self.assertAlmostEqual(output[1],5.852620488358430961e+00,5)

    def testParalacticAngle(self):
        arg1=1.507444663929565554e+00 
        arg2=-4.887258694875344922e-01
        
        output=self.cat.paralacticAngle(arg1,arg2)
        
        self.assertAlmostEqual(output,1.381600229503358701e+00,6)
        
def suite():
    utilsTests.init()
    suites = []
    suites += unittest.makeSuite(astrometryUnitTest)
    return unittest.TestSuite(suites)

def run(shouldExit = False):
    utilsTests.run(suite(),shouldExit)

if __name__ == "__main__":
    run(True)
