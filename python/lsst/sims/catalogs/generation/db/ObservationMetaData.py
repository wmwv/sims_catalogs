import numpy
import inspect
from .spatialBounds import SpatialBounds
from lsst.sims.utils import haversine, Site

__all__ = ["ObservationMetaData"]

class ObservationMetaData(object):
    """Observation Metadata

    This class contains any metadata for a query which is associated with
    a particular telescope pointing, including bounds in RA and DEC, and
    the time of the observation.

    **Parameters**

        * unrefracted[RA,Dec] float
          The coordinates of the pointing (in degrees)

        * boundType characterizes the shape of the field of view.  Current options
          are 'box, and 'circle'

        * boundLength is the characteristic length scale of the field of view in degrees.
          If boundType is 'box', boundLength can be a float(in which case boundLength is
          half the length of the side of each box) or boundLength can be a numpy array
          in which case the first argument is
          half the width of the RA side of the box and the second argument is half the
          Dec side of the box.
          If boundType is 'circle,' this will be the radius of the circle.
          The bound will be centered on the point (unrefractedRA, unrefractedDec)

        * mjd : float (optional)
          The MJD of the observation

        * bandpassName : a char (e.g. 'u') or list (e.g. ['u', 'g', 'z'])
          denoting the bandpasses used for this particular observation

        * phoSimMetadata : dict (optional)
          a dictionary containing metadata used by PhoSim

        * m5: float or list (optional)
          this should be the 5-sigma limiting magnitude in the bandpass or
          bandpasses specified in bandpassName.  Ultimately, m5 will be stored
          in a dict keyed to the bandpassName (or Names) you passed in, i.e.
          you will be able to access m5 from outside of this class using, for
          example:

          myObservationMetaData.m5['u']

        * skyBrightness: float (optional) the magnitude of the sky in the
          filter specified by bandpassName

        * rotSkyPos float (optional)
          The orientation of the telescope (see PhoSim documentation) in degrees.
          This is used by the Astrometry mixins in sims_coordUtils

    **Examples**::
        >>> data = ObservationMetaData(boundType='box', unrefractedRA=5.0, unrefractedDec=15.0,
                    boundLength=5.0)

    """
    def __init__(self, boundType=None, boundLength=None,
                 mjd=None, unrefractedRA=None, unrefractedDec=None, rotSkyPos=0.0,
                 bandpassName='r', phoSimMetadata=None, site=None, m5=None, skyBrightness=None):

        self._bounds = None
        self._boundType = boundType
        self._mjd = mjd
        self._bandpass = bandpassName
        self._skyBrightness = skyBrightness

        if rotSkyPos is not None:
            self._rotSkyPos = numpy.radians(rotSkyPos)
        else:
            self._rotSkyPos = None

        if unrefractedRA is not None:
            self._unrefractedRA = numpy.radians(unrefractedRA)
        else:
            self._unrefractedRA = None

        if unrefractedDec is not None:
            self._unrefractedDec = numpy.radians(unrefractedDec)
        else:
            self._unrefractedDec = None

        if boundLength is not None:
            if isinstance(boundLength, float):
                self._boundLength = numpy.radians(boundLength)
            else:
                try:
                    self._boundLength = []
                    for ll in boundLength:
                        self._boundLength.append(numpy.radians(ll))
                except:
                    raise RuntimeError("You seem to have passed something that is neither a float nor " +
                                       "list-like as boundLength to ObservationMetaData")
        else:
            self._boundLength = None

        if site is not None:
            self._site=site
        else:
            self._site=Site()

        if site is not None:
            self._site=site
        else:
            self._site=Site()

        if phoSimMetadata is not None:
            self.assignPhoSimMetaData(phoSimMetadata)
        else:
            self._phoSimMetadata = None

        #this should be done after phoSimMetadata is assigned, just in case
        #assignPhoSimMetadata overwrites unrefractedRA/Dec
        if self.bounds is None:
            self.buildBounds()

        if m5 is None:
            self._m5 = None
        else:
            bandpassIsList = False
            m5IsList = False
            if hasattr(self.bandpass, '__iter__'):
                bandpassIsList = True

            if hasattr(m5, '__iter__'):
                m5IsList = True

            if bandpassIsList and not m5IsList:
                raise RuntimeError('You passed a list of bandpass names' + \
                                   'but did not pass a list of m5s to ObservationMetaData')

            if m5IsList and not bandpassIsList:
                raise RuntimeError('You passed a list of m5s ' + \
                                    'but did not pass a list of bandpass names to ObservationMetaData')


            if m5IsList:
                if len(m5) != len(self.bandpass):
                    raise RuntimeError('The list of m5s you passed to ObservationMetaData ' + \
                                       'has a different length than the list of bandpass names you passed')

            #now build the m5 dict
            if bandpassIsList:
                self._m5 = {}
                for b, m in zip(self._bandpass, m5):
                    self._m5[b] = m
            else:
                self._m5 = {self._bandpass:m5}

    @property
    def summary(self):
        mydict = {}
        mydict['site'] = self.site

        mydict['boundType'] = self.boundType
        mydict['boundLength'] = self.boundLength
        mydict['unrefractedRA'] = self.unrefractedRA
        mydict['unrefractedDec'] = self.unrefractedDec
        mydict['rotSkyPos'] = self.rotSkyPos

        mydict['mjd'] = self.mjd
        mydict['bandpass'] = self.bandpass
        mydict['skyBrightness'] = self.skyBrightness
        # mydict['m5'] = self.m5

        mydict['phoSimMetadata'] = self.phoSimMetadata

        return mydict

    def buildBounds(self):
        if self._boundType is None:
            return

        if self._boundLength is None:
            raise RuntimeError("ObservationMetadata cannot assign a bounds; it has no boundLength")

        if self._unrefractedRA is None or self._unrefractedDec is None:
            raise RuntimeError("ObservationMetadata cannot assign a bounds; it has no unrefractedRA/Dec")

        self._bounds = SpatialBounds.getSpatialBounds(self._boundType, self._unrefractedRA, self._unrefractedDec,
                                                     self._boundLength)

    def assignPhoSimMetaData(self, metaData):
        """
        Assign the dict metaData to be the associated metadata dict of this object
        """

        self._phoSimMetadata = metaData

        #overwrite member variables with values from the phoSimMetadata
        if self._phoSimMetadata is not None and 'Opsim_expmjd' in self._phoSimMetadata:
            self._mjd = self._phoSimMetadata['Opsim_expmjd'][0]

        if self._phoSimMetadata is not None and 'Unrefracted_RA' in self._phoSimMetadata:
            self._unrefractedRA = self._phoSimMetadata['Unrefracted_RA'][0]

        if self._phoSimMetadata is not None and 'Opsim_rotskypos' in self._phoSimMetadata:
            self._rotSkyPos = self.phoSimMetadata['Opsim_rotskypos'][0]

        if self._phoSimMetadata is not None and 'Unrefracted_Dec' in self._phoSimMetadata:
            self._unrefractedDec = self._phoSimMetadata['Unrefracted_Dec'][0]

        if self._phoSimMetadata is not None and 'Opsim_filter' in self._phoSimMetadata:
            self._bandpass = self._phoSimMetadata['Opsim_filter'][0]

        #in case this method was called after __init__ and unrefractedRA/Dec were
        #overwritten by this method
        if self._bounds is not None:
            self.buildBounds()

    @property
    def unrefractedRA(self):
        return self._unrefractedRA

    @property
    def unrefractedDec(self):
        return self._unrefractedDec

    @property
    def boundLength(self):
        return self._boundLength

    @property
    def boundType(self):
        return self._boundType

    @property
    def bounds(self):
        return self._bounds

    @property
    def rotSkyPos(self):
        return self._rotSkyPos

    @property
    def m5(self):
        return self._m5

    @property
    def site(self):
        return self._site

    @property
    def mjd(self):
        return self._mjd

    @property
    def bandpass(self):
        return self._bandpass

    @property
    def skyBrightness(self):
        return self._skyBrightness

    @property
    def phoSimMetadata(self):
        return self._phoSimMetadata
