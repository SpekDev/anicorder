CREATE DATABASE IF NOT EXISTS anicorder;

USE anicorder;

CREATE TABLE IF NOT EXISTS anime (
	id INT NOT NULL AUTO_INCREMENT,
	english_title VARCHAR(255) NOT NULL,
	status ENUM(
		'tba',
		'tbw',
		'watching',
		'completed',
		'dropped'
	) NOT NULL DEFAULT 'watching',
	episode INT NOT NULL DEFAULT 1,
	time_watched_in_seconds INT NOT NULL DEFAULT 0,

	PRIMARY KEY (id),
);
