--
-- Alter field default_language on dataset
--
ALTER TABLE `dictionary_dataset` DROP FOREIGN KEY `dictionary_dataset_default_language_id_c91900f0_fk_dictionar`;
ALTER TABLE `dictionary_dataset` RENAME COLUMN `default_language_id` TO `default_language`;
ALTER TABLE `dictionary_dataset` ADD CONSTRAINT `dictionary_dataset_default_language_9c3d6b17_fk_dictionar` FOREIGN KEY (`default_language`) REFERENCES `dictionary_language` (`id`);
--
-- Alter field translation_languages on dataset
--
-- (no-op)
