"""Instance Catalog"""
import warnings
import numpy as np
import inspect
import re
import copy
from lsst.sims.utils import defaultSpecMap
from lsst.sims.utils import ObservationMetaData

__all__ = ["InstanceCatalog"]


class InstanceCatalogMeta(type):
    """Meta class for registering instance catalogs.

    When any new type of instance catalog class is created, this registers it
    in a `registry` class attribute, available to all derived instance
    catalogs.
    """
    @staticmethod
    def convert_to_underscores(name):
        """convert, e.g. CatalogName to catalog_name"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def __new__(cls, name, bases, dct):
        # check if attribute catalog_type is specified.
        # If not, create a default
        if 'registry' in dct:
            warnings.warn("registry class attribute should not be "
                          "over-ridden in InstanceCatalog classes. "
                          "Proceed with caution")
        if 'catalog_type' not in dct:
            dct['catalog_type'] = cls.convert_to_underscores(name)

        dct['_cached_columns'] = {}
        dct['_compound_columns'] = {}
        dct['_compound_column_names'] = {}

        return super(InstanceCatalogMeta, cls).__new__(cls, name, bases, dct)

    def __init__(cls, name, bases, dct):
        # check if 'registry' is specified.
        # if not, then this is the base class: add the registry
        if not hasattr(cls, 'registry'):
            cls.registry = {}

        # add this class to the registry
        if cls.catalog_type in cls.registry:
            raise ValueError("Catalog Type %s is duplicated"
                             % cls.catalog_type)
        cls.registry[cls.catalog_type] = cls

        # add methods for default columns
        for default in cls.default_columns:
            setattr(cls, 'default_%s'%(default[0]),
                    lambda self, value=default[1], type=default[2]:
                    np.array([value for i in xrange(len(self._current_chunk))], dtype=type))

        # store compound columns and check for collisions
        #
        #  We create a forward and backward mapping.
        #  The dictionary cls._compound_columns maps the compound column
        #   name to the multiple individual columns it represents.
        #  The dictionary cls._compound_column_names maps the individual
        #   column names to the compound column that contains them
        for key in dir(cls):
            if not key.startswith('get_'):
                continue
            compound_getter = getattr(cls, key)
            if not hasattr(compound_getter, '_compound_column'):
                continue

            for col in compound_getter._colnames:
                try:
                    getter = 'get_'+col
                except TypeError:
                    raise ValueError("column names in compound "
                                     "decorator must be strings")

                if hasattr(cls, getter):
                    raise ValueError("column name '%s' in compound getter "
                                     "'%s' conflicts with getter '%s'"
                                     % (col, key, getter))

                elif col in cls._compound_column_names:
                    raise ValueError("duplicate compound column name: '%s'"
                                     % col)

                else:
                    cls._compound_column_names[col] = key
            cls._compound_columns[key] = compound_getter._colnames

        return super(InstanceCatalogMeta, cls).__init__(name, bases, dct)


class _MimicRecordArray(object):
    """An object used for introspection of the database colums.

    This mimics a numpy record array, but when a column is referenced,
    it logs the reference and returns zeros.
    """
    def __init__(self):
        self.referenced_columns = set()

    def __getitem__(self, column):
        self.referenced_columns.add(column)
        return np.empty(0)

    def __len__(self):
        return 0


class InstanceCatalog(object):
    """ Base class for instance catalogs generated by simulations.

    Instance catalogs include a dictionary of numpy arrays which contains
    core data. Additional arrays can be appended as ancillary data.

    Catalog types and Object types are defined in the CatalogDescription class
    catalogType =  TRIM, SCIENCE, PHOTCAL, DIASOURCE, MISC, INVALID
    objectType = Point, Moving, Sersic, Image, Artefact, MISC
    catalogTable is name of the database table queried
    dataArray dictionary of numpy arrays of data
    """

    __metaclass__ = InstanceCatalogMeta

    # These are the class attributes to be specified in any derived class:
    catalog_type = 'instance_catalog'
    column_outputs = None
    specFileMap = defaultSpecMap
    default_columns = []
    cannot_be_null = []  # a list of columns which, if null, cause a row not to be printed by write_catalog()
    default_formats = {'S': '%s', 'f': '%.4f', 'i': '%i'}
    override_formats = {}
    transformations = {}
    delimiter = ", "
    comment_char = "#"
    endline = "\n"
    _pre_screen = False  # if true, write_catalog() will check database query results against
                         # cannot_be_null before calculating getter columns

    @classmethod
    def new_catalog(cls, catalog_type, *args, **kwargs):
        """Return a new catalog of the given catalog type"""
        if catalog_type in cls.registry:
            return cls.registry[catalog_type](*args, **kwargs)
        elif inspect.isclass(catalog_type) and issubclass(catalog_type, InstanceCatalog):
            return catalog_type(*args, **kwargs)
        else:
            raise ValueError("Unrecognized catalog_type: %s"
                             % str(catalog_type))

    @classmethod
    def is_compound_column(cls, column_name):
        """Return true if the given column name is a compound column"""
        getfunc = "get_%s" % column_name
        if hasattr(cls, getfunc):
            if hasattr(getattr(cls, getfunc), '_compound_column'):
                return True
        return False

    def iter_column_names(self):
        """Iterate the column names, expanding any compound columns"""

        for column in self._column_outputs:
            if self.is_compound_column(column):
                for col in getattr(getattr(self, "get_" + column), '_colnames'):
                    yield col
            else:
                yield column

    def __init__(self, db_obj, obs_metadata=None, column_outputs=None,
                 constraint=None, specFileMap=None):

        """
        @param [in] db_obj is an instantiation of the CatalogDBObject class,
        which provide connection to a specific database table

        see sims_catalogs_generation/python/lsst/sims/catalogs/generation/db/dbConnection.py

        @param [in] obs_metadata is an instantiation of the ObservationMetaData class
        characterizing a specific telescope observation

        see sims_catalogs_generation/python/lsst/sims/catalogs/generation/db/ObservationMetaData.py

        @param [in] column_outputs is a list of column names to be output
        in the catalog.  This is optional and will be appended to the list
        of column_outputs defined int he class definition.

        @param [in] constraint is an optional SQL constraint to be applied to the
        database query

        @param [in] specFileMap is an instantiation of the SpecMap class

        (defined in sims_catalogs_measures/python/sims/catalogs/measures/instance/fileMaps.py)

        that maps database entries for SED names to actual file paths.  If set to None,
        the class definition of InstanceCatalog ensures that it will be set to
        defaultSpecMap, which is the correct mapping for the LSST sims_sed_library
        """

        self.verbose = db_obj.verbose

        self.db_obj = db_obj
        self._current_chunk = None

        # this dict will contain information telling the user where the columns in
        # the catalog come from
        self._column_origins = {}

        if obs_metadata is not None:
            if not isinstance(obs_metadata, ObservationMetaData):
                raise ValueError("You passed InstanceCatalog something that was not ObservationMetaData")

            self.obs_metadata = copy.deepcopy(obs_metadata)
        else:
            self.obs_metadata = ObservationMetaData()

        if self.column_outputs is not None:
            self._column_outputs = copy.deepcopy(self.column_outputs)

        if column_outputs is not None:
            if self.column_outputs is None:
                self._column_outputs = copy.deepcopy(column_outputs)
            else:
                for col in column_outputs:
                    if col not in self._column_outputs:
                        self._column_outputs.append(col)

        self._actually_calculated_columns = []  # a list of all the columns referenced by self.column_by_name
        self.constraint = constraint

        if specFileMap is not None:
            self.specFileMap = specFileMap

        self.refIdCol = self.db_obj.getIdColKey()

        self._column_cache = {}

        # self._column_origins_switch tells column_by_name to log where it is getting
        # the columns in self._column_origins (we only want to do that once)
        self._column_origins_switch = True

        # now we will create and populate a list containing the names of
        # all of the columns which this InstanceCatalog can return.
        # Note: this needs to happen before self._check_requirements()
        # is called in case any getters depend on the contents of
        # _all_available_columns.  That way, self._check_requirements()
        # can verify that the getter will run the way it is actually
        # being called.
        self._all_available_columns = []

        for name in self.db_obj.columnMap.keys():
            if name not in self._all_available_columns:
                self._all_available_columns.append(name)

        for name in self._compound_column_names:
            if name not in self._all_available_columns:
                self._all_available_columns.append(name)

        for name in self._compound_columns:
            if name not in self._all_available_columns:
                self._all_available_columns.append(name)

        for name in dir(self):
            if name[:4] == 'get_':
                columnName = name[4:]
                if columnName not in self._all_available_columns:
                    self._all_available_columns.append(columnName)
            elif name[:8] == 'default_':
                columnName = name[8:]
                if columnName not in self._all_available_columns:
                    self._all_available_columns.append(columnName)

        if not hasattr(self, '_column_outputs'):
            self._column_outputs = []

            # because asking for a compound_column means asking for
            # its individual sub-columns, which means those columns
            # will get listed twice in the catalog
            for name in self._all_available_columns:
                if name not in self._compound_columns:
                    self._column_outputs.append(name)

        self._check_requirements()

    def _set_current_chunk(self, chunk, column_cache=None):
        """Set the current chunk and clear the column cache"""
        self._current_chunk = chunk
        if column_cache is None:
            self._column_cache = {}
        else:
            self._column_cache = column_cache

    def db_required_columns(self):
        """Get the list of columns required to be in the database object."""
        saved_cache = self._cached_columns
        saved_chunk = self._current_chunk
        self._set_current_chunk(_MimicRecordArray())

        for col_name in self.iter_column_names():
            # just call the column: this will log queries to the database.
            self.column_by_name(col_name)

        db_required_columns = list(self._current_chunk.referenced_columns)

        default_columns_set = set(el[0] for el in self.default_columns)
        required_columns_set = set(db_required_columns)
        required_columns_with_defaults = default_columns_set & required_columns_set

        self._set_current_chunk(saved_chunk, saved_cache)

        return db_required_columns, list(required_columns_with_defaults)

    def column_by_name(self, column_name, *args, **kwargs):
        """Given a column name, return the column data"""

        if (isinstance(self._current_chunk, _MimicRecordArray) and
            column_name not in self._actually_calculated_columns):

            self._actually_calculated_columns.append(column_name)

        getfunc = "get_%s" % column_name
        if hasattr(self, getfunc):
            function = getattr(self, getfunc)

            if self._column_origins_switch:
                self._column_origins[column_name] = self._get_class_that_defined_method(function)

            return function(*args, **kwargs)
        elif column_name in self._compound_column_names:
            getfunc = self._compound_column_names[column_name]
            function = getattr(self, getfunc)

            if self._column_origins_switch and column_name:
                self._column_origins[column_name] = self._get_class_that_defined_method(function)

            compound_column = function(*args, **kwargs)
            return compound_column[column_name]
        elif (isinstance(self._current_chunk, _MimicRecordArray) or
              column_name in self._current_chunk.dtype.names):

            if self._column_origins_switch:
                self._column_origins[column_name] = 'the database'

            return self._current_chunk[column_name]
        else:

            if self._column_origins_switch:
                self._column_origins[column_name] = 'default column'

            return getattr(self, "default_%s"%column_name)(*args, **kwargs)

    def _check_requirements(self):
        """Check whether the supplied db_obj has the necessary column names"""

        missing_cols = []
        self._active_columns = []
        cols, defaults = self.db_required_columns()

        for col in cols:
            if col not in self.db_obj.columnMap:
                missing_cols.append(col)
            else:
                self._active_columns.append(col)

        self._column_origins_switch = False  # do not want to log column origins any more

        if len(missing_cols) > 0:
            nodefault = []
            for col in missing_cols:
                if col not in defaults:
                    nodefault.append(col)
                else:
                    # Because some earlier part of the code copies default columns
                    # into the same place as columns that exist natively in the
                    # database, this is where we have to mark columns that are
                    # set by default
                    self._column_origins[col] = 'default column'

            if len(nodefault) > 0:
                raise ValueError("Required columns missing from database: "
                                 "({0})".format(', '.join(nodefault)))

        if self.verbose:
            self.print_column_origins()

    def _make_line_template(self, chunk_cols):
        templ_list = []
        for i, col in enumerate(self.iter_column_names()):
            templ = self.override_formats.get(col, None)

            if templ is None:
                typ = chunk_cols[i].dtype.kind
                templ = self.default_formats.get(typ)

            if templ is None:
                if self.verbose:
                    warnings.warn("Using raw formatting for column '%s' "
                                  "with type %s" % (col, chunk_cols[i].dtype))
                templ = "%s"
            templ_list.append(templ)

        return self.delimiter.join(templ_list) + self.endline

    def write_header(self, file_handle):
        column_names = list(self.iter_column_names())
        templ = [self.comment_char, ]
        templ += ["%s" for col in column_names]
        file_handle.write("{0}".format(self.comment_char + self.delimiter.join(column_names)) +
                          self.endline)

    def write_catalog(self, filename, chunk_size=None,
                      write_header=True, write_mode='w'):
        """
        Write query self.db_obj and write the resulting InstanceCatalog to
        an ASCII output file

        @param [in] filename is the name of the ASCII file to be written

        @param [in] chunk_size is an optional parameter telling the CompoundInstanceCatalog
        to query the database in manageable chunks (in case returning the whole catalog
        takes too much memory)

        @param [in] write_header a boolean specifying whether or not to add a header
        to the output catalog (default True)

        @param [in] write_mode is 'w' if you want to overwrite the output file or
        'a' if you want to append to an existing output file (default: 'w')
        """

        self._write_pre_process()

        self._query_and_write(filename, chunk_size=chunk_size,
                              write_header=write_header,
                              write_mode=write_mode,
                              obs_metadata=self.obs_metadata,
                              constraint=self.constraint)

    def _query_and_write(self, filename, chunk_size=None, write_header=True,
                         write_mode='w', obs_metadata=None, constraint=None):
        """
        This method queries db_obj, and then writes the resulting recarray
        to the specified ASCII output file.

        @param [in] filename is the name of the ASCII file to be written

        @param [in] obs_metadata is an ObservationMetaData instantiation
        characterizing the telescope pointing (optional)

        @param [in] constraint is an optional SQL constraint applied to the database query.

        @param [in] chunk_size is an optional parameter telling the CompoundInstanceCatalog
        to query the database in manageable chunks (in case returning the whole catalog
        takes too much memory)

        @param [in] write_header a boolean specifying whether or not to add a header
        to the output catalog (default True)

        @param [in] write_mode is 'w' if you want to overwrite the output file or
        'a' if you want to append to an existing output file (default: 'w')
        """

        file_handle = open(filename, write_mode)
        if write_header:
            self.write_header(file_handle)

        query_result = self.db_obj.query_columns(colnames=self._active_columns,
                                                 obs_metadata=obs_metadata,
                                                 constraint=constraint,
                                                 chunk_size=chunk_size)

        for chunk in query_result:
            self._write_recarray(chunk, file_handle)

        file_handle.close()

    def _write_pre_process(self):
        """
        This function verifies the catalog's required columns, initializes
        some member variables that are required for the catalog-writing process.
        """
        db_required_columns, required_columns_with_defaults = self.db_required_columns()
        self._template = None

    def _write_recarray(self, chunk, file_handle):
        """
        This method takes a recarray (usually returned by querying db_obj),
        and writes it to the catalog.  This method also handles any transformation
        of columns that needs to happen before they are written to the catalog.

        @param [in] chunk is the recarray of queried columns to be formatted
        and written to the catalog.

        @param [in] file_handle is a file handle pointing to the file where
        the catalog is being written.
        """

        if self._pre_screen:
            # go through the database query results and remove all of those
            # rows that have already run afoul of self.cannot_be_null
            for col_name in self.cannot_be_null:
                if col_name in chunk.dtype.names:
                    str_vec = np.char.lower(chunk[col_name].astype('str'))
                    good_dexes = np.where(np.logical_and(str_vec != 'none',
                                          np.logical_and(str_vec != 'nan', str_vec != 'null')))
                    chunk = chunk[good_dexes]

        self._set_current_chunk(chunk)

        # If some columns are specified as cannot_be_null, loop over those columns,
        # removing rows that run afoul of that criterion from the chunk.
        if len(self.cannot_be_null) > 0:
            for filter_col in self.cannot_be_null:
                try:
                    filter_vals = np.char.lower(self.column_by_name(filter_col).astype('str'))
                except:
                    # apparently, the column does not exist in this catalog
                    continue

                good_dexes = np.where(np.logical_and(filter_vals != 'none',
                                      np.logical_and(filter_vals  != 'nan', filter_vals != 'null')))

                if len(good_dexes[0]) < len(chunk):
                    chunk = chunk[good_dexes]

                    # In the event that self._column_cache has already been created,
                    # update the cache so that only valid rows remain therein
                    new_cache = {}
                    if len(self._column_cache) > 0:
                        for col_name in self._column_cache:
                            new_cache[col_name] = self._column_cache[col_name][good_dexes]

                    self._set_current_chunk(chunk, column_cache=new_cache)

        chunk_cols = [self.transformations[col](self.column_by_name(col))
                      if col in self.transformations.keys() else
                      self.column_by_name(col)
                      for col in self.iter_column_names()]

        # Create the template with the first chunk
        if self._template is None:
            self._template = self._make_line_template(chunk_cols)

        # use a generator expression for lines rather than a list
        # for memory efficiency
        file_handle.writelines(self._template % line for line in zip(*chunk_cols))

    def iter_catalog(self, chunk_size=None):
        self.db_required_columns()

        query_result = self.db_obj.query_columns(colnames=self._active_columns,
                                                 obs_metadata=self.obs_metadata,
                                                 constraint=self.constraint,
                                                 chunk_size=chunk_size)
        for chunk in query_result:
            self._set_current_chunk(chunk)
            chunk_cols = [self.transformations[col](self.column_by_name(col))
                          if col in self.transformations.keys() else
                          self.column_by_name(col)
                          for col in self.iter_column_names()]
            for line in zip(*chunk_cols):
                yield line

    def iter_catalog_chunks(self, chunk_size=None):
        self.db_required_columns()

        query_result = self.db_obj.query_columns(colnames=self._active_columns,
                                                 obs_metadata=self.obs_metadata,
                                                 constraint=self.constraint,
                                                 chunk_size=chunk_size)
        for chunk in query_result:
            self._set_current_chunk(chunk)
            chunk_cols = [self.transformations[col](self.column_by_name(col))
                          if col in self.transformations.keys() else
                          self.column_by_name(col)
                          for col in self.iter_column_names()]
            chunkColMap = dict([(col, i) for i, col in enumerate(self.iter_column_names())])
            yield chunk_cols, chunkColMap

    def get_objId(self):
        return self.column_by_name(self.refIdCol)

    def get_uniqueId(self, nShift=10):
        arr = self.column_by_name(self.refIdCol)
        if len(arr) > 0:
            return np.left_shift(self.column_by_name(self.refIdCol), nShift) + \
                   self.db_obj.getObjectTypeId()
        else:
            return arr

    def _get_class_that_defined_method(self, meth):
        """
        This method will return the name of the class that first defined the
        input method.

        This is taken verbatim from
        http://stackoverflow.com/questions/961048/get-class-that-defined-method
        """

        for cls in inspect.getmro(meth.im_class):
            if meth.__name__ in cls.__dict__:
                return cls

        return None

    def print_column_origins(self):
        """
        Print the origins of the columns in this catalog
        """

        print '\nwhere the columns in ', self.__class__, ' come from'
        for column_name in self._column_origins:
            print column_name, self._column_origins[column_name]

        print '\n'

