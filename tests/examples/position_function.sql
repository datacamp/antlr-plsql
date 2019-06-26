SELECT
  SUBSTRING(address, POSITION(' ' IN address)+1, LENGTH(address))
FROM
  address;