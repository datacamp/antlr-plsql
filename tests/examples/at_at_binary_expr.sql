SELECT title, description
FROM film
WHERE to_tsvector(title) @@ to_tsquery('elf');