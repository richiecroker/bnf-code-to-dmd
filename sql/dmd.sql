  SELECT
  "vmp" AS type, # create type column, shows whether VMP or AMP
  vmp.id AS id, # VMP code
  vmp.nm AS nm, # VMP name
  vmp.vtm AS vtm, # VTM code
  vtm.nm AS vtm_nm, # VTM name
  bnf_code, # BNF code
  vpidprev AS vmp_previous, # Previous VMP code
  vpiddt AS vmp_previous_date # Date that previous VMP code changed
FROM
  ebmdatalab.dmd.vmp_full AS vmp
LEFT OUTER JOIN
  dmd.vtm AS vtm
ON
  vmp.vtm = vtm.id

UNION ALL # join VMP and AMP tables together to form single table
SELECT
  "amp" AS type,
  amp.id,
  amp.descr,
  vmp.vtm,
  vtm.nm AS vtm_nm,
  amp.bnf_code AS bnf_code,
  NULL AS amp_previous,
  NULL AS amp_previous_date
FROM
  ebmdatalab.dmd.amp_full AS amp
INNER JOIN
  dmd.vmp AS vmp # join VMP to AMP table to get VMP codes to obtain VTM information
ON
  amp.vmp = vmp.id
LEFT OUTER JOIN
  dmd.vtm AS vtm 
ON
  vmp.vtm = vtm.id 
