use aiken/collection/list
use aiken/crypto.{sha2_256}
use cardano/transaction.{
  Datum, InlineDatum, NoDatum, OutputReference, Transaction,
}

pub type MeasurementDatum {
  sensor_id: ByteArray,
  expected_sha256: ByteArray,
}

pub type MeasurementRedeemer {
  sensor_id: ByteArray,
  measurement: ByteArray,
}

fn measurement_matches(datum: Datum, redeemer: Data) -> Bool {
  expect InlineDatum(raw_datum) = datum
  expect expected: MeasurementDatum = raw_datum
  expect claimed: MeasurementRedeemer = redeemer

  claimed.sensor_id == expected.sensor_id && sha2_256(claimed.measurement) == expected.expected_sha256
}

validator sensor_hash_validation {
  spend(
    _datum: Option<Data>,
    redeemer: Data,
    own_ref: OutputReference,
    self: Transaction,
  ) {
    expect Some(input) = list.find(
      self.inputs,
      fn(input) { input.output_reference == own_ref },
    )

    measurement_matches(input.output.datum, redeemer)
  }

  else(_) {
    fail
  }
}

const measurement = "AGRI-002|2026-11-20T10:00:00Z|23.6|61"

fn fixture_datum() -> Datum {
  let expected: Data = MeasurementDatum {
    sensor_id: "AGRI-002",
    expected_sha256: #"b76cef7674424ef76659031a5cf22f1d9b38316c2fe1e71cdbd12c75fc30ac26",
  }
  InlineDatum(expected)
}

fn claim(id: ByteArray, bytes: ByteArray) -> Data {
  let encoded: Data = MeasurementRedeemer { sensor_id: id, measurement: bytes }
  encoded
}

test matching_sensor_and_measurement() {
  measurement_matches(fixture_datum(), claim("AGRI-002", measurement))
}

test different_sensor_id() {
  !measurement_matches(fixture_datum(), claim("AGRI-001", measurement))
}

test modified_temperature() {
  !measurement_matches(
    fixture_datum(),
    claim("AGRI-002", "AGRI-002|2026-11-20T10:00:00Z|23.7|61"),
  )
}

test modified_humidity() {
  !measurement_matches(
    fixture_datum(),
    claim("AGRI-002", "AGRI-002|2026-11-20T10:00:00Z|23.6|62"),
  )
}

test modified_serialization() {
  !measurement_matches(
    fixture_datum(),
    claim("AGRI-002", "AGRI-002|2026-11-20T10:00:00Z|23.60|61"),
  )
}

test missing_datum() fail {
  measurement_matches(NoDatum, claim("AGRI-002", measurement))
}

test malformed_redeemer() fail {
  let malformed: Data = 0
  measurement_matches(fixture_datum(), malformed)
}
