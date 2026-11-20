--
-- Create model MorphemeFeedback
--
CREATE TABLE `feedback_morphemefeedback` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `date` datetime(6) NOT NULL, `comment` longtext NOT NULL, `status` varchar(10) NOT NULL, `morpheme_id` integer NULL, `translation_id` integer NOT NULL, `user_id` integer NOT NULL);
--
-- Remove field correct from signfeedback
--
ALTER TABLE `feedback_signfeedback` DROP COLUMN `correct`;
--
-- Remove field isAuslan from signfeedback
--
ALTER TABLE `feedback_signfeedback` DROP COLUMN `isAuslan`;
--
-- Remove field kwnotbelong from signfeedback
--
ALTER TABLE `feedback_signfeedback` DROP COLUMN `kwnotbelong`;
--
-- Remove field like from signfeedback
--
ALTER TABLE `feedback_signfeedback` DROP COLUMN `like`;
--
-- Remove field suggested from signfeedback
--
ALTER TABLE `feedback_signfeedback` DROP COLUMN `suggested`;
--
-- Remove field use from signfeedback
--
ALTER TABLE `feedback_signfeedback` DROP COLUMN `use`;
--
-- Remove field whereused from signfeedback
--
ALTER TABLE `feedback_signfeedback` DROP COLUMN `whereused`;
--
-- Add field gloss to signfeedback
--
ALTER TABLE `feedback_signfeedback` ADD COLUMN `gloss_id` integer NULL , ADD CONSTRAINT `feedback_signfeedback_gloss_id_919d57ce_fk_dictionary_gloss_id` FOREIGN KEY (`gloss_id`) REFERENCES `dictionary_gloss`(`id`);
ALTER TABLE `feedback_morphemefeedback` ADD CONSTRAINT `feedback_morphemefee_morpheme_id_1d8a445a_fk_dictionar` FOREIGN KEY (`morpheme_id`) REFERENCES `dictionary_morpheme` (`gloss_ptr_id`);
ALTER TABLE `feedback_morphemefeedback` ADD CONSTRAINT `feedback_morphemefee_translation_id_1be082df_fk_dictionar` FOREIGN KEY (`translation_id`) REFERENCES `dictionary_translation` (`id`);
ALTER TABLE `feedback_morphemefeedback` ADD CONSTRAINT `feedback_morphemefeedback_user_id_f8e2562b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
