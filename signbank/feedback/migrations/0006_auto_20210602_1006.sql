--
-- Add field althandshape_handshapefk to missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` ADD COLUMN `althandshape_handshapefk_id` integer NULL , ADD CONSTRAINT `feedback_missingsign_althandshape_handsha_1c282262_fk_dictionar` FOREIGN KEY (`althandshape_handshapefk_id`) REFERENCES `dictionary_handshape`(`machine_value`);
--
-- Add field handshape_handshapefk to missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` ADD COLUMN `handshape_handshapefk_id` integer NULL , ADD CONSTRAINT `feedback_missingsign_handshape_handshapef_48987530_fk_dictionar` FOREIGN KEY (`handshape_handshapefk_id`) REFERENCES `dictionary_handshape`(`machine_value`);
