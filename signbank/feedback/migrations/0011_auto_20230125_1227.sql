--
-- Remove field user from interpreterfeedback
--
ALTER TABLE `feedback_interpreterfeedback` DROP FOREIGN KEY `feedback_interpreterfeedback_user_id_a073e59d_fk_auth_user_id`;
ALTER TABLE `feedback_interpreterfeedback` DROP COLUMN `user_id`;
--
-- Remove field althandshape from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_althandshape_id_5b6bb149_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `althandshape_id`;
--
-- Remove field direction from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_direction_id_d194a1a0_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `direction_id`;
--
-- Remove field handbodycontact from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_handbodycontact_id_f42e38d4_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `handbodycontact_id`;
--
-- Remove field handform from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_handform_id_7d2f6286_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `handform_id`;
--
-- Remove field handinteraction from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_handinteraction_id_5ca952f1_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `handinteraction_id`;
--
-- Remove field handshape from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_handshape_id_312a1c3f_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `handshape_id`;
--
-- Remove field location from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_location_id_c708aea4_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `location_id`;
--
-- Remove field movementtype from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_movementtype_id_878ada0e_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `movementtype_id`;
--
-- Remove field relativelocation from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_relativelocation_id_04ade78a_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `relativelocation_id`;
--
-- Remove field repetition from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `repetition`;
--
-- Remove field smallmovement from missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` DROP FOREIGN KEY `feedback_missingsign_smallmovement_id_0bf6ab45_fk_dictionar`;
ALTER TABLE `feedback_missingsignfeedback` DROP COLUMN `smallmovement_id`;
--
-- Add field signlanguage to missingsignfeedback
--
ALTER TABLE `feedback_missingsignfeedback` ADD COLUMN `signlanguage_id` integer NULL , ADD CONSTRAINT `feedback_missingsign_signlanguage_id_007c7fad_fk_dictionar` FOREIGN KEY (`signlanguage_id`) REFERENCES `dictionary_signlanguage`(`id`);
--
-- Delete model InterpreterFeedback
--
DROP TABLE `feedback_interpreterfeedback` CASCADE;
