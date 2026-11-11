--
-- Remove field handshape from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `handshape_id`;
--
-- Rename field handshape_handshapefk on missingsignfeedback to handshape
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_handshape_handshapef_48987530_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` RENAME COLUMN `handshape_handshapefk_id` TO `handshape_id`;
ALTER TABLE `feedback_missingsignfeedback` ADD CONSTRAINT `feedback_missingsign_handshape_id_312a1c3f_fk_dictionar` FOREIGN KEY (`handshape_id`) REFERENCES `dictionary_handshape` (`machine_value`);
--
-- Remove field althandshape from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_althandshape_id_5b6bb149_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `althandshape_id`;
--
-- Rename field althandshape_handshapefk on missingsignfeedback to althandshape
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_althandshape_handsha_1c282262_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` RENAME COLUMN `althandshape_handshapefk_id` TO `althandshape_id`;
ALTER TABLE `feedback_missingsignfeedback` ADD CONSTRAINT `feedback_missingsign_althandshape_id_5b6bb149_fk_dictionar` FOREIGN KEY (`althandshape_id`) REFERENCES `dictionary_handshape` (`machine_value`);
