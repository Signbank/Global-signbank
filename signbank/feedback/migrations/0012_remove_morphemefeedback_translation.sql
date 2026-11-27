--
-- Remove field translation from morphemefeedback
--
ALTER TABLE `feedback_morphemefeedback` DROP FOREIGN KEY `feedback_morphemefee_translation_id_1be082df_fk_dictionar`;
ALTER TABLE `feedback_morphemefeedback` DROP COLUMN `translation_id`;
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
