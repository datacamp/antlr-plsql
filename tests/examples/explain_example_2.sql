EXPLAIN
SELECT
   f.film_id,
   title,
   name category_name
FROM
   film f
   INNER JOIN film_category fc
       ON fc.film_id = f.film_id
   INNER JOIN category c
       ON c.category_id = fc.category_id
ORDER BY
   title;