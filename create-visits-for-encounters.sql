-- create-visits-for-encounters.sql
-- This is a SQL script that will create visits for already-existing encounters
-- in the OpenMRS database. It creates one visit per patient-day; thus all
-- encounters that take place on the same day are assumed to be part of the
-- same visit.
--
-- Note that this means that if a real-world patient visit involves multiple
-- encounters that happen on different sides of midnight UTC, they will appear
-- as different visits.
--
-- Parameters:
--   @visit_type_id: the visit_type_id to use for the created visits. If you
--     need to use different visit_type_ids for different types of encounters,
--     do separate runs of this script varying this parameter and
--     encounter_type_exclusions as necessary.
--   @encounter_type_exclusions: a comma-separated string enumerating the 
--     encounter_type_ids which should be excluded from these visits.
--
-- `location_id` and `creator` are assumed to be the same across each
-- encounter group (i.e., per patient-day). If they are not, it is undefined
-- which of the different values will be used.
--

SET @visit_type_id = 1;
SET @encounter_type_exclusions = '2';  /* a comma-separated string like '1,2,3' */

-- Create the visits
INSERT INTO visit
       (patient_id,   visit_type_id,  date_started,   date_stopped,   location_id,   creator,   date_created, voided, uuid)
SELECT  e.patient_id, @visit_type_id, e.date_started, e.date_stopped, e.location_id, e.creator, now(),        0,      uuid()
FROM
(
    SELECT patient_id, 
           Subtime(Min(encounter_datetime), '00:05:00') AS date_started,  /* visit must start before first enc */
           Addtime(Max(encounter_datetime), '00:05:00') AS date_stopped,  /* visit must end after last enc */
           location_id,
           creator
    FROM   encounter 
    WHERE  FIND_IN_SET(encounter_type, @encounter_type_exclusions) = 0
    GROUP  BY patient_id, 
              Date(encounter_datetime) 
) AS e;

-- Add the visit_ids to their encounters
UPDATE encounter e 
       INNER JOIN visit v 
               ON e.patient_id = v.patient_id 
                  AND Date(e.encounter_datetime) = Date(v.date_started) 
SET    e.visit_id = v.visit_id
WHERE FIND_IN_SET(e.encounter_type, @encounter_type_exclusions) = 0;
