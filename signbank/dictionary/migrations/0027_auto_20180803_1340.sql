
--
-- Add field default_language to dataset
--
ALTER TABLE `dictionary_dataset` ADD COLUMN `default_language_id` integer NULL , ADD CONSTRAINT `dictionary_dataset_default_language_id_c91900f0_fk_dictionar` FOREIGN KEY (`default_language_id`) REFERENCES `dictionary_language`(`id`);
