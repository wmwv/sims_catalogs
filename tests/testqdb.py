#!/usr/bin/env python
from lsst.sims.generation.db import queryDB

if __name__ == "__main__":
  myqdb = queryDB.queryDB(chunksize=1000)
  ic = myqdb.getInstanceCatalogById(85748128)

  while ic is not None:
      print myqdb._start
      ic = myqdb.getNextChunk()
